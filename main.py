import pygame as pg
from input import InputHandler
from game_manager import GameManeger, RollBackManager
from multiprocessing import Value
import id_maker
from time import perf_counter

ROLLBACK_TEST = False
WHITE = (255, 255, 255)
Meiryo_20 = pg.font.SysFont("Meiryo",20)


class MainApp:
    SCREENRECT = pg.Rect(0, 0, 1280, 720)
    APP_NAME = "SmashBalls"
    FPS = 240

    def __init__(self):
        pg.init()
        self.init_app()

    # 初期化
    def init_app(self):
        self.run = True
        self.winstyle = 0

        self.window = pg.display.set_mode(self.SCREENRECT.size, self.winstyle)
        pg.display.set_caption(self.APP_NAME)

        self.joy_chara_map = {}
        self.chara_input_map = {}
        self.joysticks = {}

        self.process_running = Value('b', True)
        self.logic_rate = Value('d', 0)
        self.game_mgr = GameManeger(self.process_running, self.logic_rate)
        self.game_mgr.init_game()
        self.rollback_mgr = RollBackManager()
        self.rollback_inputs = [[] for _ in range(64*60*60)]
        self.key_chara_id = self.add_character("red")

        self.polling_clock = pg.time.Clock()
        self.display_clock = pg.time.Clock()


        if ROLLBACK_TEST:
            self.rollback_game_process = Process(target=self.rollback_mgr.mainloop, daemon=True)
            self.rollback_game_process.start()
            self.surface1 = pg.Surface((1280,720)).convert_alpha()
            self.surface2 = pg.Surface((1280,720)).convert_alpha()

    
    def add_character(self, color):
        chara_id = id_maker.make_id(self.chara_input_map.values())
        self.game_mgr.add_character(color, chara_id)
        self.rollback_mgr.add_character(color, chara_id)
        self.chara_input_map[chara_id] = InputHandler()
        return chara_id

    def remove_character(self, chara_id):
        self.game_mgr.remove_character(chara_id)
        self.rollback_mgr.remove_character(chara_id)
        del self.chara_input_map[chara_id]

    def display_handler(self):
        tick = self.display_clock.tick()
        if ROLLBACK_TEST:
            self.window.fill(0)
            self.game_mgr.draw_game(self.surface1, tick)
            self.rollback_mgr.draw_game(self.surface2, tick)
            reduced_s1 = pg.transform.smoothscale(self.surface1, (640,360))
            reduced_s2 = pg.transform.smoothscale(self.surface2, (640,360))
            self.window.blit(reduced_s1,(0,240))
            self.window.blit(reduced_s2,(640,240))
        else:
            self.game_mgr.draw_game(self.window, tick)
        # fps表示
        fps_surface = Meiryo_20.render(f"FPS : {int(self.display_clock.get_fps())}  LOGIC : {int(self.logic_rate.value)}  POLLING : {int(self.polling_clock.get_fps())}", True, WHITE)
        self.window.blit(fps_surface,dest=(5, 2))
        pg.display.flip()

    # イベント処理
    def event_handler(self):
        input_changed = {chara_id: False for chara_id in self.chara_input_map.keys()}

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.run = False
            # コントローラー接続・切断
            elif event.type == pg.JOYDEVICEADDED:
                joy = pg.joystick.Joystick(event.device_index)
                self.joysticks[joy.get_instance_id()] = joy
                self.joy_chara_map[joy.get_instance_id()] = self.add_character("red")
                self.chara_input_map[self.joy_chara_map[joy.get_instance_id()]].connect_joy(joy.get_numbuttons(), joy.get_numaxes(), joy.get_numhats())
                print(f"{joy.get_name()} connencted!")
            elif event.type == pg.JOYDEVICEREMOVED:
                print(f"{self.joysticks[event.instance_id].get_name()} disconnected!")
                self.remove_character(self.joy_chara_map[event.instance_id])
                del self.joy_chara_map[event.instance_id]
                del self.joysticks[event.instance_id]
            # 入力処理
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_0:
                    if self.game_mgr.FPS == 64:
                        self.game_mgr.FPS = self.rollback_mgr.FPS = 4
                        self.game_mgr.FRAME_LATENCY = self.rollback_mgr.FRAME_LATENCY = 1/self.game_mgr.FPS
                    else:
                        self.game_mgr.FPS = self.rollback_mgr.FPS = 64
                        self.game_mgr.FRAME_LATENCY = self.rollback_mgr.FRAME_LATENCY = 1/self.game_mgr.FPS
                input_changed[self.key_chara_id] |= self.chara_input_map[self.key_chara_id].keydown(event.key)
            elif event.type == pg.KEYUP:
                input_changed[self.key_chara_id] |= self.chara_input_map[self.key_chara_id].keyup(event.key)
            elif event.type == pg.JOYBUTTONDOWN:
                input_changed[self.joy_chara_map[event.instance_id]] |= self.chara_input_map[self.joy_chara_map[event.instance_id]].buttondown(event.button)
            elif event.type == pg.JOYBUTTONUP:
                input_changed[self.joy_chara_map[event.instance_id]] |= self.chara_input_map[self.joy_chara_map[event.instance_id]].buttonup(event.button)
            elif event.type == pg.JOYAXISMOTION:
                input_changed[self.joy_chara_map[event.instance_id]] |= self.chara_input_map[self.joy_chara_map[event.instance_id]].axismove(event.axis, event.value)
            elif event.type == pg.JOYHATMOTION:
                input_changed[self.joy_chara_map[event.instance_id]] |= self.chara_input_map[self.joy_chara_map[event.instance_id]].hatmove(event.hat, event.value)

        if any(input_changed.values()):
            for chara_id, changed in input_changed.items():
                if changed:
                    #if not self.rollback_mgr.regist_input(chara_id, self.chara_input_map[chara_id], self.rollback_mgr.current_state.frame_number-8):
                    #    print("Input is skipped")
                    self.game_mgr.regist_input(chara_id, self.chara_input_map[chara_id])
                    self.rollback_inputs[self.game_mgr.state.frame_number].append((chara_id,self.chara_input_map[chara_id].copy()))

                    print(f"f_num:{self.game_mgr.state.frame_number} ID({chara_id})'s input : {self.chara_input_map[chara_id]}")

        DELAY_FRAME = 4
        for chara_id, input in self.rollback_inputs[self.rollback_mgr.current_state.frame_number-DELAY_FRAME]:
            self.rollback_mgr.regist_input(chara_id, input, self.rollback_mgr.current_state.frame_number-DELAY_FRAME)
            print(f"rollback_num:{self.rollback_mgr.current_state.frame_number-DELAY_FRAME} {input}")
        self.rollback_inputs[self.rollback_mgr.current_state.frame_number-DELAY_FRAME]=[]

    # メインループ(イベントループ処理)
    # メインスレッドで動作すること
    def mainloop(self):
        POLLING_RATE = 1000

        last_render_time = perf_counter()
        while self.run:
            #self.polling_clock.tick(POLLING_RATE)
            self.polling_clock.tick_busy_loop(POLLING_RATE)
            self.event_handler()
            # 描画処理
            if perf_counter() > last_render_time + 1/self.FPS:
                last_render_time += 1/self.FPS
                if perf_counter() - last_render_time > 1/self.FPS*2:    # 描画が遅れている場合は時間を修正
                    last_render_time = perf_counter()
                self.display_handler()

        # 正常終了時処理
        self.process_running.value = False
        self.rollback_mgr.run = False
        self.game_mgr.game_process.join()
        if ROLLBACK_TEST:
            self.rollback_game_process.join()
        print("Bye!")

if __name__ == '__main__':
    # ロールバックのテストを行うかどうか
    # コマンドライン引数により制御
    import sys
    args = len(sys.argv[1:])
    if args == 0:
        ROLLBACK_TEST = False
    elif args == 1:
        value = sys.argv[1]
        if value.lower() == "true":
            ROLLBACK_TEST = True
        elif value.lower() == "false":
            ROLLBACK_TEST = False
        else:
            print(f"エラー: 引数はTrueかFalseのみ受け付けます。", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"エラー: 引数が多すぎます。TrueかFalseのみ入力してください。", file=sys.stderr)
        sys.exit(1)
    app = MainApp()
    app.mainloop()
    pg.quit()