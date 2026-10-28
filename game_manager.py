from gamelogic import GameState
from time import perf_counter, sleep
from ctypes import windll
from render import GameRenderer
import pickle


""" ゲーム進行の管理 """
class GameManeger:
    FPS = 64
    FRAME_LATENCY = 1/FPS
    KO_UPDATE_LATENCY = 1/16

    def __init__(self):
        self.run = True
        def dummy():
            pass
        self.update_func = dummy    # ゲームが更新される際に呼び出される関数(通信等)
        self.frame_rate = 0         # フレームレートの保存

        self.available_color = ["red", "green"] # 利用可能なキャラの色
        self.state = GameState()
        self.renderer = GameRenderer()

    """ ゲームの初期化 """
    def init_game(self):
        self.state.init_game()

    """ ゲームのリスタート """
    def try_restart(self):
        if not self.state.status == "play":
            self.state.init_game()
            self.renderer.ko_animator.reset()

    """ キャラの追加 """
    def add_character(self, color, id):
        if color in self.available_color:
            return self.state.add_character(color, id)
        else:
            raise ValueError(f"{color} is not available color")

    """ キャラの削除 """
    def remove_character(self, id):
        self.state.remove_character(id)

    """ 指定idのキャラへ入力を登録 """    
    def regist_input(self, id, new_input):
        self.state.regist_input(id, new_input)

    """ ゲームの描画 """
    def draw_game(self, window, tick):
        self.renderer.render(window, tick, self.state)

    """ ゲームのメイン処理 """
    def mainloop(self):
        windll.winmm.timeBeginPeriod(1)     # タイマーの精度向上
        frame_time = [perf_counter()]*2     # フレームレートの観測用リスト
        delay = 0
        ko_update_timing = 0
        while self.run:
            start = perf_counter()

            if self.state.status == "play":
                self.state.update()     # ゲーム状況を更新
                self.update_func()      # フレーム毎実行処理
                # ゲーム終了判定
                if self.state.status != "play":
                    self.renderer.ko_animation_start()    # K.O.演出開始
            else:
                # KO演出中は更新頻度を落とす
                if ko_update_timing + self.KO_UPDATE_LATENCY < perf_counter():
                    self.state.update()
                    ko_update_timing = perf_counter()

            self.renderer.update(self.FRAME_LATENCY)    # 描画時に必要な更新

            # フレーム計測
            frame_time[1] = perf_counter()
            self.frame_rate = 1/(frame_time[1]-frame_time[0])
            frame_time[0] = perf_counter()

            # フレーム遅延処理
            delay = perf_counter()-start
            if self.FRAME_LATENCY-delay > 0.001:
                sleep(int((self.FRAME_LATENCY-delay)/0.001)*0.001)
            while perf_counter()-start < self.FRAME_LATENCY:
                pass
        windll.winmm.timeEndPeriod(1)   

# pickleを利用した高速なdeepcopy
def fast_copy(obj):
    return pickle.loads(pickle.dumps(obj))

""" GameManagerと同様にゲーム進行の管理を行うクラス。ロールバック処理を追加するためにGameManagerから分割
    現在のStateから見て[1F前,2F前,4F前,8F前...]のフレームがstate_bufferに保存
    必要に応じて自動でロールバック """
class RollBackManager:
    STATE_BUFFER_SIZE = 8                           # ロールバック用のバッファサイズ
    ROLLBACK_ABLE_SIZE = 2**(STATE_BUFFER_SIZE-1)   # ロールバック可能なフレーム数
    FPS = 64
    FRAME_LATENCY = 1/FPS

    def __init__(self):
        self.run = True
        def dummy():
            pass
        self.update_func = dummy                # ゲームが更新される際に呼び出される関数(通信等)
        self.frame_rate = 0                     # フレームレートの保存
        self.available_color = ["red", "green"] # 利用可能なキャラの色

        self.current_state = GameState()
        self.state_buffer = [fast_copy(self.current_state) for _ in range(self.STATE_BUFFER_SIZE)]
        self.input_buffer = [[] for _ in range(self.ROLLBACK_ABLE_SIZE)]
        self.character_change = [[] for _ in range(self.ROLLBACK_ABLE_SIZE)]

        self.renderer = GameRenderer()

    """ キャラの追加 """
    def add_character(self, color, id):
        if color in self.available_color:
            self.current_state.add_character(color, id)
            self.character_change[self.current_state.frame_number % self.ROLLBACK_ABLE_SIZE].append(("add", color, id))
        else:
            raise ValueError(f"{color} is not available color")

    """ キャラの削除 """
    def remove_character(self, id):
        chara = [_ for _ in self.current_state.characters_list if _.id == id][0]
        self.current_state.remove_character(id)
        self.character_change[self.current_state.frame_number % self.ROLLBACK_ABLE_SIZE].append(("remove", chara.color, id))
    
    """ 指定フレーム番号の指定idのキャラへ入力を登録 """
    def regist_input(self, id, new_input, frame_number=-1):
        # 最新に登録
        if frame_number == -1:
            self.current_state.regist_input(id, new_input)
            return True
        # それ以外（ロールバック）
        else:
            if frame_number < self.current_state.frame_number - self.ROLLBACK_ABLE_SIZE or frame_number < self.state_buffer[-1].frame_number:
                return False
            input_index = frame_number % self.ROLLBACK_ABLE_SIZE
            self.input_buffer[input_index].append((id, new_input.copy()))

            base_state_index = min([i for i, state in enumerate(self.state_buffer) if state.frame_number <= frame_number])
            base_state = fast_copy(self.state_buffer[base_state_index])
            
            for i, num in reversed([(i,state.frame_number) for i, state in enumerate(self.state_buffer[:base_state_index])]):
                self.update_to(base_state, num)
                self.state_buffer[i] = fast_copy(base_state)
            self.update_to(base_state, self.current_state.frame_number)
            self.current_state = base_state
            return True
            
    """ 指定のフレームまで入力履歴を参照しながらupdateし続ける """
    def update_to(self, state, frame_number):
        base_index, goal_index = state.frame_number % self.ROLLBACK_ABLE_SIZE, frame_number % self.ROLLBACK_ABLE_SIZE

        if base_index <= goal_index:
            for i in range(base_index, goal_index):
                for change, color, id in self.character_change[i]:
                    if change == "add":
                        state.add_character(color, id)
                    elif change == "remove":
                        state.remove_character(id)
                for id, input in self.input_buffer[i]:
                    state.regist_input(id, input)
                state.update()
        else:
            for i in range(base_index, self.ROLLBACK_ABLE_SIZE):
                for change, color, id in self.character_change[i]:
                    if change == "add":
                        state.add_character(color, id)
                    elif change == "remove":
                        state.remove_character(id)
                for id, input in self.input_buffer[i]:
                    state.regist_input(id, input)
                state.update()
            for i in range(0, goal_index):
                for change, color, id in self.character_change[i]:
                    if change == "add":
                        state.add_character(color, id)
                    elif change == "remove":
                        state.remove_character(id)
                for id, input in self.input_buffer[i]:
                    state.regist_input(id, input)
                state.update()

    """ ゲームの描画 """
    def draw_game(self, window, tick):
        self.renderer.render(window, tick, self.current_state)

    """ ゲームのメイン処理 """
    def mainloop(self):
        windll.winmm.timeBeginPeriod(1)     # タイマーの精度向上
        frame_time = [perf_counter()]*2     # フレームレートの観測用リスト
        delay = 0
        while self.run:
            start = perf_counter()

            self.current_state.update()     # ゲーム状況を更新
            self.update_func()              # フレーム毎実行処理
            # バッファの更新
            index = self.current_state.frame_number % self.ROLLBACK_ABLE_SIZE
            self.input_buffer[index] = []
            self.character_change[index] = []
            for i, state in enumerate(self.state_buffer):
                if state.frame_number < self.current_state.frame_number-2**i:
                    self.update_to(state, self.current_state.frame_number-2**i)

            # フレーム計測
            frame_time[1] = perf_counter()
            self.frame_rate = 1/(frame_time[1]-frame_time[0])
            frame_time[0] = perf_counter()

            # フレーム遅延処理
            delay = perf_counter()-start
            if self.FRAME_LATENCY-delay > 0.001:
                sleep(int((self.FRAME_LATENCY-delay)/0.001)*0.001)
            while perf_counter()-start < self.FRAME_LATENCY:
                pass
        windll.winmm.timeEndPeriod(1)
