from pygame.math import lerp, Vector2
from ctypes import windll
from time import perf_counter, sleep
from input import InputHandler
from random import randint
import gameconst


# ユーティリティ関数
def closest(user, obj_list):
    if obj_list is None or len(obj_list)==0:
        return None
    distance_list = [user.pos.distance_to(obj.pos) for obj in obj_list]
    return obj_list[distance_list.index(min(distance_list))]

def angle_between(a:Vector2, b:Vector2):
    angle_gap = -(a.rotate(-90).angle_to(b.rotate(-90)))
    if angle_gap>180:
        angle_gap -= 360
    elif angle_gap<-180:
        angle_gap += 360
    return angle_gap
 


""" ゲーム状況が再現可能な情報を保存するクラス
    入力などの情報を付加しながらゲーム状況を進めることもできる """
class GameState:
    """ 初期化 """
    def __init__(self):
        self.stage = Stage()
        self.characters_list = []
        self.init_game()

    def init_game(self):
        self.frame_number = 0

    """ キャラの追加 """
    def add_character(self, color, id):
        character = Character(color=color, my_id=id)
        self.characters_list.append(character)
        # 各キャラクターのターゲットを更新
        for character in self.characters_list:
            character.target_list = [_ for _ in self.characters_list if _ != character]
        return character

    """ キャラの削除 """
    def remove_character(self, id):
        for character in [_ for _ in self.characters_list if _.id == id]:
            self.characters_list.remove(character)
        # 各キャラクターのターゲットを更新
        for chara in self.characters_list:
            chara.target_list = [_ for _ in self.characters_list if _ != chara]

    """ 入力の登録(不可逆的な変更) """
    def regist_input(self, id, new_input:InputHandler):
        for character in [_ for _ in self.characters_list if _.id == id]:
            character.input_update(new_input)

    """ ゲーム状況を更新してフレームを生成 """
    def update(self):
        self.frame_number += 1
        self.stage.update()
        # リスト順による判定の優先順位を排除するためキャラ情報を優先して更新
        for character in self.characters_list:
            character.update(self.stage)
        for character in self.characters_list:
            character.objects_update(self.stage)


""" ゲームステージ全体の情報の管理するクラス """
class Stage:
    WIDTH = 1280
    HEIGHT = 720
    GND_HEIGHT = 100
    def __init__(self):
        self.init_stage()

    def init_stage(self):
        self.platforms = []
        self.platforms.append( Platform(self.WIDTH*1/4-210/2-15, self.WIDTH*1/4+210/2-15, self.GND_HEIGHT+130) )
        self.platforms.append( Platform(self.WIDTH*2/4-210/2,    self.WIDTH*2/4+210/2,    self.GND_HEIGHT+220) )
        self.platforms.append( Platform(self.WIDTH*3/4-210/2+15, self.WIDTH*3/4+210/2+15, self.GND_HEIGHT+130) )

    def update(self):
        pass

    def get_platforms(self):
        return self.platforms

class Platform:
    """ 空中に浮く台 """
    EDGE_WIDTH = 10
    THICK = 10
    def __init__(self,x1,x2,y):
        self.x = [round(x1), round(x2)]
        self.y = round(y)

    def __contains__(self, item:Vector2):
        return (self.x[0]-self.EDGE_WIDTH <= item[0] <= self.x[1]+self.EDGE_WIDTH and self.y-self.THICK <= item[1] <= self.y)

    def is_above(self, item:Vector2):
        return (self.x[0]-self.EDGE_WIDTH <= item[0] <= self.x[1]+self.EDGE_WIDTH and self.y <= item[1])

    def is_below(self, item:Vector2):
        return (self.x[0]-self.EDGE_WIDTH <= item[0] <= self.x[1]+self.EDGE_WIDTH and item[1] <= self.y-self.THICK)

class GameObject:
    def __init__(self, pos:Vector2, speed:Vector2):
        self.pos = pos.copy()
        self.speed = speed.copy()

    def update(self):
        self.pos += self.speed

class Character(GameObject):
    def __init__(self, color, my_id="", input=InputHandler()):
        self.CONST = gameconst.CharacterConst()

        self.color = color
        self.radius = self.CONST.radius

        self.id = my_id
        GameObject.__init__( self, Vector2(Stage.WIDTH/4, Stage.GND_HEIGHT+self.radius*2), Vector2(0,5) )

        self.on_ground = True       # 接地判定（台上もTrue）
        self.on_platform = False    # 台上の判定
        self.hopping = False        # 跳ね返り
        self.double_jumped = False  # ダブルジャンプを行った後かの判定
        self.restrict_jump = False  # (ガード時など)高さ制限のある判定
        self.jump_interval = 0      # 2段ジャンプまでの間隔カウント

        self.hp = self.CONST.hp_max
        self.combo = 0              # コンボ(ダメージ軽減)の回数
        self.combo_count = 0        # コンボ継続時間
        self.no_damage_count = 0    # 無敵継続時間
        self.blowed = False         # 吹っ飛ばされ判定
        self.after_blow_count = 0   # 吹っ飛び直後の特殊動作(空気抵抗減少)のカウント
        self.target_list = []       # 攻撃が狙える相手のリスト
        self.action_busy = False    # 動作が占有されているかどうか

        self.stop_frame = 0     # ヒットストップする時間を保存
        self.stop_count = 0     # ヒットストップをカウント
        self.shake_ratio = 0
        self.shake_offset = Vector2(0, 0)

        self.effects = []
        self.sounds = []
        self.Input = InputHandler()
        self.InputActions = []

        # 戦闘機能
        self.shield = Shield(user=self)
        if self.color == "red":
            # 射撃
            self.energy_gun = EnergyGun(user=self)
            self.drone = DroneManager(user=self)
            self.sync_shot = SyncShooter(user=self)
            # ハンマー攻撃
            self.hammer = Hammer(user=self)
        elif self.color == "green":
            # 射撃
            self.knife = KnifeManager(user=self)
            self.shuriken = ShurikenManager(user=self)

    """ 入力(InputHandler)が更新される処理 """
    def input_update(self, new_input:InputHandler):
        # ジャンプ
        if (new_input.direction.y==1 and self.Input.direction.y!=1):
            self.InputActions.append("jump")

        #近接攻撃 KeyDown
        if (new_input.attack==True and self.Input.attack==False) and (not self.action_busy or self.shield.status=="recovery"):
            if self.color =="red":
                self.hammer.start()
        #近接攻撃 KeyUp
        if (self.Input.attack==True and new_input.attack==False) and (not self.action_busy or self.shield.status=="recovery"):
            pass

        #シールド KeyDown
        if (new_input.shield==True and self.Input.shield==False) and (not self.action_busy or self.shield.status!="wait") and self.no_damage_count==0:
            self.shield.shield_start()
        #シールド KeyUp
        if (self.Input.shield==True and new_input.shield==False) and (not self.action_busy or self.shield.status!="wait"):
            self.shield.shield_stop()

        #スキル1 KeyDown
        if (new_input.skills[0]==True and self.Input.skills[0]==False):
            if self.color =="red" and not self.action_busy:
                self.energy_gun.lockon()
            elif self.color == "green" and not self.action_busy:
                self.knife.throw_start()
        #スキル1 KeyUp
        if (self.Input.skills[0]==True and new_input.skills[0]==False):
            if self.color =="red":
                self.energy_gun.shoot()

        #スキル2 KeyDown
        if (new_input.skills[1]==True and self.Input.skills[1]==False):
            if self.color =="red" and not self.action_busy:
                self.drone.throw_start()
            elif self.color == "green" and not self.action_busy:
                self.shuriken.throw_start()
        #スキル2 KeyUp
        if (self.Input.skills[1]==True and new_input.skills[1]==False):
            pass

        #スキル3 KeyDown
        if (new_input.skills[2]==True and self.Input.skills[2]==False):
            if self.color =="red" and (self.sync_shot.shoot_count==self.sync_shot.CONST.bullet_max or not self.action_busy):
                self.sync_shot.shoot()
        #スキル3 KeyUp
        if (self.Input.skills[2]==True and new_input.skills[2]==False):
            pass

        self.Input = new_input.copy()

    """ 音声情報の追加 """
    def set_sound(self, name):
        self.sounds.append(name)

    """ ヒットストップの設定 """
    def set_stop(self, stop, shake = 0):
        self.stop_count = self.stop_frame = int(stop)
        self.shake_ratio = shake

    """ フレーム毎の更新処理 """
    def update(self, stage:Stage):

        # エフェクト更新
        for ef in self.effects:
            ef.update()
            if not ef.active:
                self.effects.remove(ef)

        # ヒットストップ時処理（振動はupdate内で処理する）
        if self.stop_count:
            self.stop_count -= 1
            shake = int(self.shake_ratio*self.stop_count/self.stop_frame)+1
            random_side = (-1)**randint(0,1)
            self.shake_offset = Vector2( int( (-1)**(self.stop_count//2)*(randint(0,shake//2)+round(shake/2))), int( random_side*(randint(0,shake//2)+round(shake/2)) ) )
            if self.on_ground:
                self.shake_offset.y = 0
            return None
        else:
            self.stop_frame = 0
            self.shake_offset = Vector2(0, 0)

        # ダメージ直後カウント更新
        if self.after_blow_count>0:
            self.after_blow_count -= 1
        # コンボ継続時間更新
        if self.combo_count>0:
            self.combo_count -= 1
        # 無敵継続時間更新
        elif self.no_damage_count>0:
            self.no_damage_count -= 1
            if self.no_damage_count == 0 and (self.on_ground==False or self.blowed):
                self.no_damage_count = 1
        if self.combo_count==0:
            self.combo = 0

        # シールド継続入力受付
        if self.Input.shield and (not self.action_busy and self.no_damage_count==0):
            self.shield.shield_start()

        # 物理演算
        if self.on_ground:
            # 接地時の判定リセット
            self.hopping = False
            self.jump_interval = 0
            self.double_jumped = False
            # 吹っ飛び判定更新
            if abs(self.speed.x)<self.CONST.speed_max:
                self.blowed = False
            # 跳ね
            if self.speed.y<0:
                self.speed.y = round(abs(self.speed.y)*self.CONST.bounce)
                if self.speed.y != 0:
                    self.hopping = True
            # 摩擦
            if self.speed.x>0:
                self.speed.x -= self.CONST.friction
                if self.speed.x < self.CONST.friction*2:
                    self.speed.x=0
            elif self.speed.x<0:
                self.speed.x += self.CONST.friction
                if self.speed.x > -self.CONST.friction*2:
                    self.speed.x=0
            # 動力
            if self.Input.direction.x==1:
                # 初速条件 = (水平速度が小さい　もしくは　(跳ねてる　かつ　初速以下))
                if (abs(self.speed.x) < self.CONST.start_condition or (self.hopping and self.speed.x<self.CONST.start_speed)):
                    self.speed.x = self.CONST.start_speed
                else:
                    if self.speed.x>0:
                        self.speed.x += self.CONST.accelarate + self.CONST.friction
                    else:
                        self.speed.x += self.CONST.accelarate
                self.speed.x = min(self.speed.x, self.CONST.speed_max)
            if self.Input.direction.x==-1:
                if (abs(self.speed.x) < self.CONST.start_condition or (self.hopping and self.speed.x>-self.CONST.start_speed)):
                    self.speed.x = -self.CONST.start_speed
                else:
                    if self.speed.x<0:
                        self.speed.x -= self.CONST.accelarate + self.CONST.friction
                    else:
                        self.speed.x -= self.CONST.accelarate
                self.speed.x = max(self.speed.x, -self.CONST.speed_max)
            # ジャンプ
            if "jump" in self.InputActions and self.hopping==False:
                self.jump_interval = self.CONST.next_jump_interval
                if self.restrict_jump:
                    self.speed.y = self.CONST.restrict_jump
                else:
                    if self.on_platform:
                        self.speed.y = self.CONST.platform_jump
                    else:
                        self.speed.y = self.CONST.normal_jump
            # ステージからの飛び降り
            if self.on_platform and self.Input.direction.y==-1:
                self.speed.y += self.CONST.drop_speed
        else:
            if self.jump_interval>0:
                self.jump_interval -= 1
            # 重力
            if self.after_blow_count>0:
                self.speed.y -= 3/2
            elif self.hopping == False:
                if -1/4 < self.speed.y <= 0:
                    self.speed.y -= 1/8
                elif -3/4 < self.speed.y <= -1/4:
                    self.speed.y -= 1/4
                elif -7/4 < self.speed.y <= -3/4:
                    self.speed.y -= 1/2
                elif -13/4 < self.speed.y <= -7/4:
                    self.speed.y -= 3/4
                elif -5 < self.speed.y <= -13/4:
                    self.speed.y -= 7/8
                elif -30 < self.speed.y:
                    self.speed.y -= self.CONST.gravity
            else:
                self.speed.y -= self.CONST.gravity
            # 空気抵抗(吹っ飛び時)
            if self.blowed:
                if self.after_blow_count>0:
                    grip_ratio = self.CONST.grip_weak
                elif abs(self.speed.x)>self.CONST.speed_max:
                    grip_ratio = self.CONST.grip_strong
                else:
                    grip_ratio = 0
                if self.speed.x>0:
                    self.speed.x -= grip_ratio
                elif self.speed.x<0:
                    self.speed.x += grip_ratio
            # 空中ジャンプ
            if "jump" in self.InputActions and not self.double_jumped and self.jump_interval==0 and not self.hopping and not self.restrict_jump:
                self.speed.y = self.CONST.air_jump
                self.double_jumped = True
                self.effects.append(Effect("airjump", self.pos))
            # 動力(跳ね・吹っ飛び時のみ)
            jump_height = self.pos.y-self.radius-stage.GND_HEIGHT
            if (self.hopping and jump_height < self.CONST.hopping_height) or self.blowed:
                if self.Input.direction.x==1 and self.speed.x<self.CONST.speed_max:
                    self.speed.x += self.CONST.air_power
                    self.speed.x = min(self.speed.x, self.CONST.speed_max)
                elif self.Input.direction.x==-1 and self.speed.x>-self.CONST.speed_max:
                    self.speed.x -= self.CONST.air_power
                    self.speed.x = max(self.speed.x, -self.CONST.speed_max)

        # 座標更新
        GameObject.update(self)

        # 座標を調整
        if self.pos.x < self.radius:
            self.pos.x = self.radius
            if self.blowed:
                self.speed.x *= -1
                self.speed.y += 10
        elif self.pos.x > stage.WIDTH-self.radius:
            self.pos.x = stage.WIDTH-self.radius
            if self.blowed:
                self.speed.x *= -1
                self.speed.y += 10
        # 接地判定
        if self.pos.y-self.radius <= stage.GND_HEIGHT:
            self.on_ground = True
            self.on_platform = False
            self.pos.y = stage.GND_HEIGHT + self.radius
        else:
            for platform in stage.platforms:
                foot_pos = self.pos-Vector2(0, self.radius)
                last_pos = foot_pos-self.speed
                if (foot_pos in platform or (platform.is_above(last_pos) and platform.is_below(foot_pos))) and self.speed.y<=0 and not self.Input.direction.y==-1:
                    self.on_ground = True
                    self.on_platform = True
                    self.pos.y = platform.y+self.radius
                    break
            else:
                self.on_ground = False
                self.on_platform = False

        self.InputActions.clear()

    """ Character傘下にいるオブジェクトの更新を行う """
    def objects_update(self, stage:Stage):
        self.shield.update(stage)   # 反射した弾も更新する必要があるため、引数にstageを渡す
        if self.color == "red":
            self.hammer.update()
            self.energy_gun.update(stage)
            self.drone.update(stage)
            self.sync_shot.update(stage)
        elif self.color == "green":
            self.knife.update(stage)
            self.shuriken.update(stage)

    """ くらい判定の確認をする 返り値:当たったオブジェクトのリスト """
    def hit_check(self, pos:Vector2, r:int, anti_bullet:bool=False, anti_shield:bool=False) -> list[GameObject]:
        hit_objects = []
        hit_objects += self.shield.hit_check(pos, r, anti_bullet=anti_bullet, anti_shield=anti_shield)

        if self.shield.status != "guard" and self.pos.distance_to(pos) < self.radius+r and (self.no_damage_count==0 or self.combo_count>0):
            hit_objects.append(self)

        if self.color == "red":
            hit_objects += self.energy_gun.hit_check(pos, r, anti_bullet=anti_bullet, anti_shield=anti_shield)
            hit_objects += self.drone.hit_check(pos, r, anti_bullet=anti_bullet, anti_shield=anti_shield)
            hit_objects += self.sync_shot.hit_check(pos, r, anti_bullet=anti_bullet, anti_shield=anti_shield)
        elif self.color == "green":
            hit_objects += self.knife.hit_check(pos, r, anti_bullet=anti_bullet, anti_shield=anti_shield)
            hit_objects += self.shuriken.hit_check(pos, r, anti_bullet=anti_bullet, anti_shield=anti_shield)
        return hit_objects

    """ ダメージとコンボの処理を行う """
    def damage_process(self, damage:int):
        # 初撃
        if self.no_damage_count==0:
            self.hp -= damage
            self.blowed = True
            self.combo += 1
            if self.color=="red":
                self.hammer.reset()
        # コンボ
        elif self.combo_count>0:
            print(f"{self.combo} Combo Damage : {damage}→{int(damage/(self.combo+1))}")
            self.hp -= int(damage/(self.combo+1))
            self.combo += 1


# エフェクト
class Effect:
    def __init__(self, name:str, pos:Vector2):
        self.name = name
        self.pos = pos.copy()
        self.count = 0
        self.active = True

    def update(self):
        self.count += 1
        if self.name == "airjump" and self.count>10:
            self.active = False


""" 弾をはじき、タイミングを合わせると近接攻撃も防ぐシールド """
class Shield:
    def __init__(self, user):
        # 定数
        self.CONST = gameconst.ShieldConst
        # 変数
        self.status = "wait"
        self.user = user
        self.pos = self.user.pos.copy()
        self.radius = self.CONST.radius_first
        self.startup_count = 0
        self.instant_count = 0
        self.recovery_count = 0
        self.hitback_bullets = []
        self.hitback_objects = []

    """ 入力開始時 """
    def shield_start(self):
        if self.status != "guard":
            self.status = "start_up"
            if self.radius != 0:
                self.startup_count = round(self.radius/self.CONST.radius_max*self.CONST.startup)
        self.user.action_busy = True

    """ 入力終了時 """
    def shield_stop(self):
        if self.status == "start_up" or self.status == "wait":
            self.reset()
        else:
            self.status = "recovery"
            self.startup_count = 0
            self.recovery_count = 0

    def reset(self):
        self.status = "wait"
        self.user.action_busy = False
        self.user.restrict_jump = False
        self.radius = self.CONST.radius_first
        self.startup_count = 0
        self.instant_count = 0
        self.recovery_count = 0

    def hit_check(self, pos, r, anti_bullet=False, anti_shield=False):
        hit_objects = []
        if self.status != "wait":
            collide_radius = max(self.user.radius, self.radius)       # 判定半径をキャラよりも大きくする
            if anti_shield and self.pos.distance_to(pos) < collide_radius+r and self.status != "wait":
                if self.instant_count > 0:
                    self.user.no_damage_count = 16
                    self.reset()
                else:
                    hit_objects.append(self)

        for bullet in self.hitback_bullets:
            hit_objects += bullet.hit_check(pos, r, anti_bullet=anti_bullet)
        for obj in self.hitback_objects:
            hit_objects += obj.hit_check(pos, r, anti_bullet=anti_bullet)

        return hit_objects

    def damage_process(self, damage:int):
        self.reset()
        if self.user.hp > damage:
            self.user.hp -= int(damage/2)


    # シールド判定
    def attack(self):
        # ヒット処理
        for enemy in self.user.target_list:
            # 相手のオブジェクトと衝突判定
            for target in enemy.hit_check(self.pos, self.radius, anti_bullet=True):
                print(f"Shield Hit {target.__class__.__name__} from {enemy.color}")
                # 弾
                if isinstance(target,LinerBullet):
                    if target.bounced:
                        target.active = False
                    else:
                        target.bounced = True
                        # 反射位置の調整（互いのキャラが接近中は無効）
                        if self.pos.distance_to(target.user.pos) >= self.radius:
                            if (target.pos-self.pos).length() == 0:
                                target.pos += Vector2(1,0)*(self.radius+target.CONST.radius) - (target.pos-self.pos)
                            else:
                                target.pos += (target.pos-self.pos).normalize()*(self.radius+target.CONST.radius) - (target.pos-self.pos)

                        # 相手の予測位置へ反射
                        enemy_predict_pos = target.user.pos + target.user.speed - target.pos
                        # 反射するための前処理
                        self.hitback_bullets.append(target)
                        if type(target)==LinerBullet:
                            if target.user.color == "red":
                                target.user.energy_gun.remove_bullet(target)
                        elif type(target)==SyncBullet:
                            target.user.sync_shot.remove_bullet(target)
                        elif type(target)==KnifeBullet:
                            target.user.knife.remove_bullet(target)

                        target.user = self.user
                        target.alive_count = 0
                        target.no_damage_count=8
                        # 反射速度を加算(キャラへ反射)
                        target.speed = 1.1*target.speed.length()*enemy_predict_pos.normalize()

                elif type(target)==Drone:
                    target.active = False

                elif type(target)==Shuriken:
                    circle_pos = target.pos + target.CONST.hit_circles[0].rel_pos
                    circle_radius = target.CONST.hit_circles[0].radius
                    # 反射位置の調整（互いのキャラが接近中は無効）
                    if self.pos.distance_to(target.user.pos) >= self.radius:
                        if (target.pos-self.pos).length() == 0:
                            target.pos += Vector2(1,0)*(self.radius + circle_radius)
                        else:
                            target.pos += (target.pos-self.pos).normalize()*(self.radius + circle_radius) - (target.pos-self.pos)
                    # 反射するための前処理
                    self.hitback_objects.append(target)
                    target.user.shuriken.remove(target)
                    # 反射処理
                    target.user = self.user
                    target.alive_count = 0
                    target.no_damage_count=8
                    target.speed *= -1
                        

    def update(self, stage:Stage):
        self.pos = self.user.pos.copy()
        # 発動前
        if self.status == "start_up":
            if self.startup_count < self.CONST.startup:
                self.radius = lerp(self.CONST.radius_first, self.CONST.radius_max, self.startup_count/self.CONST.startup)
                self.startup_count += 1
            else:
                self.status = "guard"
                self.user.restrict_jump = True
                self.instant_count = self.CONST.instant_block
        # 発動中
        elif self.status == "guard":
            self.radius = self.CONST.radius_max
            self.attack()
            if self.instant_count > 0:
                self.instant_count -= 1
        # 発動後
        elif self.status == "recovery":
            if self.recovery_count < self.CONST.recovery:
                self.recovery_count += 1
                self.radius = lerp(self.CONST.radius_max, self.user.radius, self.recovery_count/self.CONST.recovery)
            else:
                self.reset()

        for bullet in self.hitback_bullets:
            bullet.update(stage)
            if not bullet.active and not bullet.display:
                self.hitback_bullets.remove(bullet)
        for obj in self.hitback_objects:
            obj.update(stage)
            if not obj.active and not obj.display:
                self.hitback_objects.remove(obj)


""" 事前に入力された速度方向に真っ直ぐ飛翔する弾 """
class LinerBullet(GameObject):
    def __init__(self, name:str, user:Character, speed:Vector2, CONST=gameconst.LinerBulletConst() ):
        GameObject.__init__( self, user.pos, speed )
        self.CONST = CONST
        # 変数
        self.user = user
        self.alive_count = 0        # 弾の存在時間のカウント
        self.hitwait_count = 0      # ヒットストップ中の待機カウント
        self.no_damage_count = 0    # 弾に対するダメージ無敵カウント
        self.hp = self.CONST.hp_max

        self.active = True          # 弾が更新する(動く)かどうかの判定
        self.display = True         # 弾が表示されるかどうかの判定
        self.bounced = False        # シールド・台などに反射した後かどうかの判定

    def hit_check(self, pos, r, anti_bullet=False, anti_shield=False):
        for circle in self.CONST.hit_circles:
            circle_pos = self.pos + circle.rel_pos
            if anti_bullet and circle_pos.distance_to(pos) < circle.radius+r and self.active and self.no_damage_count==0:
                return [self]
        return []

    def damage_process(self, damage):
        self.hp -= damage

    def update(self, stage:Stage):
        if self.active:
            self.attack()
            if self.no_damage_count>0:
                self.no_damage_count-=1

            GameObject.update(self)

            # 地面・台との衝突判定
            for circle in self.CONST.hit_circles:
                foot, top = (self.pos + circle.rel_pos) - Vector2(0, circle.radius), (self.pos + circle.rel_pos) + Vector2(0, circle.radius)
                next_foot, next_top = foot+self.speed, top+self.speed
                for platform in stage.platforms:
                    if (self.pos+circle.rel_pos in platform or (platform.is_below(foot) and platform.is_above(next_top)) or (platform.is_above(top) and platform.is_below(next_foot))):
                        if self.bounced:
                            self.active = False
                        else:
                            self.speed.reflect_ip(Vector2(0,1))
                            self.pos.y += self.speed.y
                            self.bounced = True
                        break
                if foot[1] < stage.GND_HEIGHT:
                    if self.bounced:
                        self.active = False
                    else:
                        self.speed.reflect_ip(Vector2(0,1))
                        self.bounced = True

            # 時間管理
            self.alive_count += 1
            if self.hp<0 or self.alive_count>self.CONST.alive_frame:
                self.active = False
        else:
            if self.hitwait_count>0:
                self.hitwait_count -= 1
            else:
                self.display = False

    def attack(self):
        for circle in self.CONST.hit_circles:
            pos = self.pos + circle.rel_pos
            damage_ratio = circle.damage/self.CONST.hit_circles[0].damage
            for enemy in self.user.target_list:
                # 相手のオブジェクトと衝突判定
                for target in enemy.hit_check(pos, circle.radius, anti_bullet=True):
                    # ダメージ処理
                    target.damage_process(circle.damage)
                    # キャラに当たった
                    if type(target) == Character:
                        # 無敵処理
                        target.no_damage_count = self.CONST.no_damage_frame
                        target.combo_count = self.CONST.combo_interval
                        # ヒットストップ処理
                        if self.CONST.is_include_ratio:
                            target.set_stop( self.CONST.hit_stop*damage_ratio, self.CONST.shake*damage_ratio)
                            self.hitwait_count = int(self.CONST.hit_stop*damage_ratio/2)
                        else:
                            target.set_stop( self.CONST.hit_stop, self.CONST.shake)
                            self.hitwait_count = int(self.CONST.hit_stop/2)
                    self.active = False


""" 赤の近接攻撃（ハンマー）ダメージが高く、シールドを破壊する """
class Hammer:
    def __init__(self, user):
        # 定数
        self.CONST = gameconst.HammerConst()

        # 変数
        self.active = False
        self.motion_count = -1
        self.motion = "none"
        self.interval = 0
        self.user = user
        self.direction = "right"

        self.offset = (0,0)
        self.angle = 0

        self.distance_ratio = 1

    def reset(self):
        self.active = self.user.action_busy = False
        self.motion_count = -1
        self.motion = "none"

    def start(self):
        if self.active == False and self.interval == 0:
            self.reset()
            self.active = self.user.action_busy = True
            target = closest(self.user, self.user.target_list)
            self.offset, self.angle = self.CONST.frame_data[0][0].copy(), self.CONST.frame_data[0][1]
            if isinstance(target, Character) and target.pos.x < self.user.pos.x:
                self.direction = "left"
                self.offset.x *= -1
                self.angle *= -1
            else:
                self.direction = "right"

    def update(self):
        if self.active and self.user.stop_frame == 0:
            #更新
            self.motion_count += 1
            self.offset = self.CONST.frame_data[self.motion_count][0].copy()
            self.angle = self.CONST.frame_data[self.motion_count][1]

            if self.direction == "left":
                self.offset.x *= -1
                self.angle *= -1

            # かまえ
            if 0 <= self.motion_count < self.CONST.startup:
                self.motion = "start_up"
            # 攻撃
            elif 0 <= self.motion_count-self.CONST.startup < self.CONST.attacking:
                self.motion = "attack"
                # 攻撃処理
                self.attack()
            # フォロースルー
            elif 0 <= self.motion_count-(self.CONST.startup+self.CONST.attacking) < self.CONST.recovery:
                self.motion = "recovery"
            else:
                self.interval = self.CONST.interval
                self.reset()
        else:
            if self.interval > 0:
                self.interval -= 1

    def attack(self):
        self.distance_ratio = 1
        for circle in self.CONST.hit_circles:
            pos = self.user.pos + self.offset + circle.rel_pos.rotate(-self.angle)
            damage_ratio = circle.damage/self.CONST.hit_circles[0].damage
            # ヒット処理
            for enemy in self.user.target_list:
                # 相手のオブジェクトと衝突判定
                for target in enemy.hit_check(pos, circle.radius, anti_bullet=True, anti_shield=True):
                    target.damage_process(circle.damage)
                    #相手に当たった
                    if type(target) == Character:
                        # 距離割合の計算（食い込み補正のため）
                        self.distance_ratio = pos.distance_to(target.pos)/(circle.radius+target.radius)
                        # 無敵処理
                        target.no_damage_count = self.CONST.no_damage_frame
                        target.after_blow_count = self.CONST.after_blow_frame
                        # ヒットストップ処理
                        target.set_stop(self.CONST.hit_stop*damage_ratio+self.CONST.hit_const_stop, self.CONST.shake*damage_ratio)
                        self.user.set_stop(self.CONST.self_hit_stop*damage_ratio, self.CONST.self_shake*damage_ratio)
                        # 吹っ飛ばし処理
                        vector = self.CONST.blow_vector.copy()
                        if self.direction == "left":
                            vector.x *= -1
                        target.speed += vector
                    #シールドに当たった
                    elif type(target) == Shield:
                        # 距離割合の計算（食い込み補正のため）
                        self.distance_ratio = pos.distance_to(target.pos)/(circle.radius+target.radius)
                        # ヒットストップ処理
                        target.user.set_stop(self.CONST.shield_stop*damage_ratio+self.CONST.shield_const_stop, self.CONST.shield_shake*damage_ratio)
                        self.user.set_stop(self.CONST.shield_stop*damage_ratio, self.CONST.shield_self_shake*damage_ratio)
                    #他オブジェクトとの衝突
                    else:
                        # 距離割合の計算（食い込み補正のため）
                        for target_circle in target.CONST.hit_circles:
                            if pos.distance_to(target.pos+target_circle.rel_pos) < circle.radius+target_circle.radius:
                                self.distance_ratio = pos.distance_to(target.pos+target_circle.rel_pos)/(circle.radius+target_circle.radius)
                                break
                        # ヒットストップ処理
                        self.user.set_stop(self.CONST.self_obj_stop, self.CONST.self_obj_shake)


""" 溜めるとダメージ・速度・精度が上がる直進弾を撃つエネルギー銃(赤スキル1) """
class EnergyGun:
    def __init__(self, user):
        # 定数
        self.CONST = gameconst.EnergyGunConst()

        # 変数
        self.status = "wait"
        self.user = user
        self.target = None
        self.magazine = []
        self.shoot_count = 0        # 弾が発射された数

        self.startup_count = 0      # 弾が発射できるまでのカウント
        self.charge_count = 0       # チャージのフレームカウント
        self.interval_count = 0     # 弾が出る間隔のカウント
        self.reload_count = 0       # 装填までのカウントダウン

        self.angle = 0
        self.angle_range = self.CONST.angle_range_max

    def hit_check(self, pos, r, anti_bullet=False, anti_shield=False):
        bullet_list = []
        for bullet in self.magazine:
            bullet_list += bullet.hit_check(pos, r, anti_bullet=anti_bullet)
        return bullet_list

    def remove_bullet(self, bullet):
        self.magazine.remove(bullet)

    def update(self, stage:Stage):
        if self.reload_count>0:
            self.reload_count -= 1
            if self.reload_count==0:
                self.magazine.clear()
        if self.interval_count>0:
            self.interval_count -= 1
            if self.interval_count==0 and self.status=="wait_interval":
                self.status = "wait_shooting"

        if self.status=="lockon" or self.status=="wait_shooting":
            self.startup_count += 1
            #角度追尾
            target_vector = self.target.pos-self.user.pos
            target_angle = angle_between(Vector2(0,1), target_vector)
            if target_vector.x>=0:
                self.angle = round( lerp(90, target_angle, self.startup_count/self.CONST.startup) )
            else:
                self.angle = round( lerp(-90, target_angle, self.startup_count/self.CONST.startup) )

            if self.startup_count==self.CONST.startup:
                self.startup_count = 0
                self.charge_start()
        elif self.status=="charge":
            #角度追尾
            angle_gap = angle_between(Vector2(0,1).rotate(-self.angle), self.target.pos-self.user.pos)
            if abs(angle_gap)>self.CONST.rotate_speed:
                if angle_gap>0:
                    self.angle += self.CONST.rotate_speed
                else:
                    self.angle -= self.CONST.rotate_speed
            else:
                self.angle += angle_gap
            if self.charge_count<self.CONST.charge:
                self.charge_count += 1
                self.angle_range = round(lerp(self.CONST.angle_range_max, self.CONST.angle_range_min, self.charge_count/self.CONST.charge))

        for each in self.magazine:
            each.update(stage)

    def lockon(self):
        if self.reload_count==0:
            self.status = "lockon"
            self.user.action_busy = True
            self.target = closest(self.user, self.user.target_list)
            if self.target is None:
                self.target = self.user
            if self.target.pos.x >= self.user.pos.x:
                self.angle = 90
            else:
                self.angle = -90

    def charge_start(self):
        if self.status=="wait_shooting":
            self.shoot()
        else:
            self.status = "charge"

    def shoot(self):
        if self.reload_count==0:
            if self.status=="lockon":        #ロックオン中は射撃待機
                self.status = "wait_shooting"
            elif self.interval_count>0:
                self.status = "wait_interval"
            elif self.status=="charge" or (self.status=="wait_shooting" and self.interval_count==0):
                charge_level = (self.charge_count/self.CONST.charge)**2

                angle = self.angle + randint(-self.angle_range,self.angle_range)
                speed = round(lerp(self.CONST.speed_min, self.CONST.speed_max, charge_level)) * Vector2(0,1).rotate(-angle)

                damage = round(lerp(self.CONST.damage_min, self.CONST.damage_max, charge_level))
                alive_frame = round(lerp(self.CONST.alive_min, self.CONST.alive_max, charge_level))
                const = gameconst.EnergyBulletConst(alive_frame=alive_frame, damage=damage)

                self.magazine.append(LinerBullet(name="bullet", user=self.user, speed=speed, CONST=const))

                self.shoot_count += 1

                #変数リセット
                self.status = "wait"
                self.user.action_busy = False
                self.angle = 0
                self.angle_range = self.CONST.angle_range_max
                self.charge_count = 0
                self.interval_count = self.CONST.interval
                if self.shoot_count == self.CONST.bullet_max:
                    self.reload_count = self.CONST.reload
                    self.shoot_count = 0


""" 敵を追尾し衝突すると爆発するドローン(赤スキル2) """
class Drone(GameObject):
    def __init__(self, user, target):
        GameObject.__init__( self, user.pos, Vector2(0,0) )
        # 定数
        self.CONST = gameconst.DroneConst()
        # 変数
        self.hp = self.CONST.hp_max
        self.user = user
        self.target = target
        self.active = False         # ドローンを更新するかの判定
        self.wait = True            # 射出モーション中かの判定（表示を切らない為）
        self.display = True         # ドローンを表示するかの判定

        self.alive_count = 0        # 弾の存在時間のカウント
        self.startup_count = 0      # 射出直後に直進するフレームのカウント
        self.homing_count = 0       # 追尾する間隔のカウント
        self.hitwait_count = 0      # ヒットストップ中のカウント

    def hit_check(self, pos, r, anti_bullet=False, anti_shield=False):
        for circle in self.CONST.hit_circles:
            circle_pos = self.pos + circle.rel_pos
            if anti_bullet and circle_pos.distance_to(pos) < circle.radius+r and self.active:
                return [self]
        return []

    def damage_process(self, damage):
        self.hp -= damage

    def update(self, stage:Stage):
        if self.active:
            if self.startup_count>=self.CONST.startup:
                self.attack()
                # 追尾
                if self.homing_count>=self.CONST.homing_interval:
                    self.homing_count = 0
                    # 速度変更
                    self.speed = (self.CONST.speed_max-1)/self.CONST.speed_max*self.speed + (self.target.pos-self.pos).normalize()

                    # 速度制限
                    if self.speed.length() > self.CONST.speed_max:
                        self.speed.scale_to_length(self.CONST.speed_max)
                else:
                    self.homing_count += 1
            else:
                self.startup_count +=1

            GameObject.update(self)
            self.alive_count += 1

            # 消滅条件
            if self.hp<0 or self.alive_count>self.CONST.alive_frame:
                self.active = False
        else:
            # ヒットストップが終わるまで表示する
            if self.hitwait_count>0:
                self.hitwait_count -= 1
            # 射出モーション以外でactive=Falseなら表示を切る
            elif not self.wait:
                self.display = False
        

    def attack(self):
        for circle in self.CONST.hit_circles:
            pos = self.pos + circle.rel_pos
            for enemy in self.user.target_list:
                for target in enemy.hit_check(pos, circle.radius, anti_bullet=True):
                    # ダメージ処理
                    target.damage_process(circle.damage)
                    # キャラに当たった
                    if type(target) == Character:
                        # 無敵処理
                        target.no_damage_count = self.CONST.no_damage_frame
                        # ヒットストップ処理
                        target.set_stop( self.CONST.hit_stop, self.CONST.shake)
                        self.hitwait_count = int(self.CONST.hit_stop/2)
                    self.active = False

    def shoot(self, angle_range):
        self.active = True
        self.wait = False
        angle = angle_between(self.target.pos-self.pos, Vector2(0,1)) + randint(-angle_range,angle_range)
        self.speed = self.CONST.speed_max*Vector2(0, 1).rotate(angle)


""" ドローン(赤スキル2)の投擲・射出を管理するクラス """
class DroneManager:
    def __init__(self, user):
        self.CONST = gameconst.DroneManagerConst
        # 変数
        self.status = "wait"
        self.user = user
        self.magazine = []
        self.throwing_drone = None      # 投擲中のドローン

        self.throw_count = 0            # 投擲の経過時間カウント
        self.interval_count = 0         # ドローン射出の間隔のカウント
        self.shoot_count = 0            # ドローン射出数カウント
        self.reload_count = 0           # ドローンの再装填カウント

    def hit_check(self, pos, r, anti_bullet=False, anti_shield=False):
        drone_list = []
        for drone in self.magazine:
            drone_list += drone.hit_check(pos, r, anti_bullet=anti_bullet)
        return drone_list

    def damage_process(self, damage):
        for drone in self.magazine:
            drone.damage_process(damage)

    def update(self, stage:Stage):
        if self.reload_count>0:
            self.reload_count -= 1
            if self.reload_count==0:
                self.magazine.clear()
        # 投擲
        if self.status == "throw":
            # 投擲表現
            if self.throwing_drone.target.pos == self.user.pos:
                self.throwing_drone.pos = Vector2(0,1).rotate(270*self.throw_count/self.CONST.throw_time)*self.user.radius + self.user.pos
            else:
                self.throwing_drone.pos = (self.throwing_drone.target.pos-self.user.pos).normalize().rotate(270*self.throw_count/self.CONST.throw_time)*self.user.radius + self.user.pos
            self.throw_count += 1

            # 投げ終わりで射出
            if self.throw_count >= self.CONST.throw_time:
                self.throw_count = 0
                self.throwing_drone.shoot(self.CONST.angle_range)
                self.throwing_drone = None
                self.status = "wait"
                self.user.action_busy = False
                self.interval_count = self.CONST.interval
                self.shoot_count += 1
                if self.shoot_count >= self.CONST.drone_max:
                    self.shoot_count = 0
                    self.reload_count = self.CONST.reload
        elif self.interval_count>0:
            self.interval_count -= 1

        for drone in self.magazine:
            drone.update(stage)

    def throw_start(self):
        if self.reload_count==0 and self.status == "wait" and self.interval_count==0:
            self.status = "throw"
            #弾生成
            target = closest(self.user, self.user.target_list)
            if target==None:
                target=self.user
            self.throwing_drone = Drone(user=self.user, target=target)
            self.magazine.append(self.throwing_drone)
            self.user.action_busy = True
            if (target.pos-self.user.pos).length()!=0:
                self.throwing_drone.pos = (target.pos-self.user.pos).normalize()*self.user.radius + self.user.pos
            else:
                self.throwing_drone.pos = Vector2(1,0)*self.user.radius + self.user.pos


""" 時止め弾：複数の直進弾を空中に設置し、最後に全ての弾を同時に発射する(赤スキル3) """
class SyncBullet(LinerBullet):
    def __init__(self, user:Character, speed:Vector2, const:gameconst.SyncBulletConst):
        LinerBullet.__init__(self, "sync_bullet", user,speed,const)
        self.active = False
        self.shoot_wait = True

    def shoot(self, target):
        self.active = True
        self.shoot_wait = False
        self.speed = (target.pos-self.pos).normalize()*self.CONST.speed

    def update(self, stage:Stage):
        LinerBullet.update(self, stage)
        if self.shoot_wait:
            self.display = True


""" 時止め弾（赤スキル3) の設置・同時発射を管理するクラス"""
class SyncShooter:
    def __init__(self, user):
        self.CONST = gameconst.SyncShooterConst()
        # 変数
        self.user = user
        self.target = None
        self.magazine = []

        self.shoot_count = 0        # 設置回数のカウント
        self.reload_count = 0       # 再装填の時間カウント

    # くらい処理
    def hit_check(self, pos, r, anti_bullet=False, anti_shield=False):
        bullet_list = []
        for bullet in self.magazine:
            bullet_list += bullet.hit_check(pos, r, anti_bullet=anti_bullet)
        return bullet_list

    def damage_process(self, damage):
        for bullet in self.magazine:
            bullet.damage_process(self, damage)

    def remove_bullet(self, bullet):
        self.magazine.remove(bullet)

    # 入力
    def shoot(self):
        if self.reload_count==0:
            # 弾を設置
            if self.shoot_count < self.CONST.bullet_max:
                self.magazine.append(SyncBullet(user=self.user, speed=Vector2(), const=gameconst.SyncBulletConst()))
                self.shoot_count+=1
            # 射撃
            else:
                target = closest(self.user, self.user.target_list)
                if target == None:
                    target = self.user
                for bullet in self.magazine:
                    bullet.shoot(target)
                self.reload_count = self.CONST.reload

    # 更新処理
    def update(self, stage:Stage):
        if self.reload_count>0:
            self.reload_count -= 1
            if self.reload_count == 0:
                self.magazine.clear()
                self.shoot_count = 0
        for bullet in self.magazine:
            bullet.update(stage)


""" クナイ：高速で直線方向に進むクナイを投げなげる(緑スキル1) """
class KnifeBullet(LinerBullet):
    def __init__(self, user:Character, speed:Vector2, const:gameconst.KnifeBulletConst):
        LinerBullet.__init__(self, "knife_bullet", user,speed,const)
        self.active = False
        self.shoot_wait = True

    def shoot(self, speed:Vector2):
        self.active = True
        self.shoot_wait = False
        self.speed = speed

    def update(self, stage:Stage):
        LinerBullet.update(self, stage)
        if self.shoot_wait:
            self.display = True

""" クナイ(緑スキル1)の投擲・射出を管理するクラス """
class KnifeManager:
    def __init__(self, user):
        self.CONST = gameconst.KnifeManagerConst
        # 変数
        self.status = "wait"
        self.user = user
        self.target = None
        self.magazine = []
        self.throwing_knife = None      # 投擲中のクナイ

        self.throw_count = 0            # 投擲の経過時間カウント
        self.interval_count = 0         # クナイ射出の間隔のカウント
        self.shoot_count = 0            # クナイ射出数カウント
        self.reload_count = 0           # クナイの再装填カウント

    def hit_check(self, pos, r, anti_bullet=False, anti_shield=False):
        print(f"KnifeManager hit_check: pos={pos}, r={r}, anti_bullet={anti_bullet}, anti_shield={anti_shield}")
        knife_list = []
        for knife in self.magazine:
            knife_list += knife.hit_check(pos, r, anti_bullet=anti_bullet)
        return knife_list

    def damage_process(self, damage):
        for knife in self.magazine:
            knife.damage_process(damage)

    def remove_bullet(self, bullet):
        self.magazine.remove(bullet)

    def update(self, stage:Stage):
        if self.reload_count>0:
            self.reload_count -= 1
            if self.reload_count==0:
                self.magazine.clear()
        # 投擲
        if self.status == "throw":
            self.throw_count += 1
            # 投擲表現
            if self.target.pos == self.user.pos:
                self.throwing_knife.pos = Vector2(1,0).rotate(270*self.throw_count/self.CONST.throw_time)*(self.user.radius//3*2) + self.user.pos
            else:
                self.throwing_knife.pos = (self.target.pos-self.user.pos).normalize().rotate(270*self.throw_count/self.CONST.throw_time)*(self.user.radius//3*2) + self.user.pos

            # 投げ終わりで射出
            if self.throw_count >= self.CONST.throw_time:
                # ランダム方向を加えて射出
                rand_angle = randint(-self.CONST.angle_range,self.CONST.angle_range)
                speed = ((self.target.pos-self.throwing_knife.pos).normalize()*self.CONST.speed).rotate(rand_angle)
                self.throwing_knife.shoot(speed)

                # 変数リセット
                self.throw_count = 0
                self.throwing_knife = None
                self.status = "wait"
                self.user.action_busy = False
                self.interval_count = self.CONST.interval
                self.shoot_count += 1
                if self.shoot_count >= self.CONST.bullet_max:
                    self.shoot_count = 0
                    self.reload_count = self.CONST.reload
        elif self.interval_count>0:
            self.interval_count -= 1

        for knife in self.magazine:
            knife.update(stage)

    def throw_start(self):
        if self.reload_count==0 and self.status == "wait" and self.interval_count==0:
            self.status = "throw"
            #弾生成
            self.target = closest(self.user, self.user.target_list)
            if self.target==None:
                self.target=self.user
            self.throwing_knife = KnifeBullet(user=self.user, speed=Vector2(), const=gameconst.KnifeBulletConst())
            self.magazine.append(self.throwing_knife)
            self.user.action_busy = True
            if (self.target.pos-self.user.pos).length()!=0:
                self.throwing_knife.pos = (self.target.pos-self.user.pos).normalize()*(self.user.radius//3*2) + self.user.pos
            else:
                self.throwing_knife.pos = Vector2(1,0)*(self.user.radius//3*2) + self.user.pos


""" 手裏剣：放物線を描いて跳ね続ける弾を投げる(緑スキル2) """
class Shuriken(GameObject):
    def __init__(self, user):
        GameObject.__init__( self, user.pos, Vector2(0,0) )
        # 定数
        self.CONST = gameconst.ShurikenConst()
        # 変数
        self.hp = self.CONST.hp_max
        self.user = user
        self.active = False         # 手裏剣を更新するかの判定
        self.wait = True            # 射出モーション中かの判定（表示を切らない為）
        self.display = True         # 手裏剣を表示するかの判定

        self.alive_count = 0        # 弾の存在時間のカウント
        self.hitwait_count = 0      # ヒットストップ中のカウント

    def hit_check(self, pos, r, anti_bullet=False, anti_shield=False):
        for circle in self.CONST.hit_circles:
            circle_pos = self.pos + circle.rel_pos
            if anti_bullet and circle_pos.distance_to(pos) < circle.radius+r and self.active:
                return [self]
        return []

    def damage_process(self, damage):
        self.hp -= damage

    def update(self, stage:Stage):
        if self.active:
            self.attack()
            # 速度更新
            # 放物線を描いて動く
            self.speed.y -= self.CONST.gravity
            # 地面・台との衝突判定
            for circle in self.CONST.hit_circles:
                foot, top = (self.pos + circle.rel_pos) - Vector2(0, circle.radius), (self.pos + circle.rel_pos) + Vector2(0, circle.radius)
                next_foot, next_top = foot+self.speed, top+self.speed
                for platform in stage.platforms:
                    if (self.pos+circle.rel_pos in platform or (platform.is_below(foot) and platform.is_above(next_top)) or (platform.is_above(top) and platform.is_below(next_foot))):
                        # 反転処理(固定速度で反転)
                        self.speed.y = self.CONST.reflection_y
                        self.pos.y = platform.y + circle.radius
                if foot[1] < stage.GND_HEIGHT:
                    self.speed.y = self.CONST.reflection_y
                    self.pos.y = stage.GND_HEIGHT + circle.radius


            GameObject.update(self)
            self.alive_count += 1

            # 消滅条件
            if self.hp<0 or self.alive_count>self.CONST.alive_frame:
                self.active = False
        else:
            # ヒットストップが終わるまで表示する
            if self.hitwait_count>0:
                self.hitwait_count -= 1
            # 射出モーション以外でactive=Falseなら表示を切る
            elif not self.wait:
                self.display = False

    def attack(self):
        for circle in self.CONST.hit_circles:
            pos = self.pos + circle.rel_pos
            for enemy in self.user.target_list:
                for target in enemy.hit_check(pos, circle.radius, anti_bullet=True):
                    # ダメージ処理
                    target.damage_process(circle.damage)
                    # キャラに当たった
                    if type(target) == Character:
                        # 無敵処理
                        target.no_damage_count = self.CONST.no_damage_frame
                        # ヒットストップ処理
                        target.set_stop(self.CONST.hit_stop, self.CONST.shake)
                        self.hitwait_count = int(self.CONST.hit_stop/2)
                    self.active = False

    def shoot(self, speed:Vector2):
        self.active = True
        self.wait = False
        self.speed = speed

""" 手裏剣(緑スキル2)の投擲・射出を管理するクラス """
class ShurikenManager:
    def __init__(self, user):
        self.CONST = gameconst.ShurikenManagerConst
        # 変数
        self.status = "wait"
        self.user = user
        self.magazine = []
        self.throwing = None            # 投擲中の手裏剣
        self.throw_direction = "right"  # 投擲方向の判定（左右）

        self.throw_count = 0        # 投擲の経過時間カウント
        self.interval_count = 0     # 手裏剣射出の間隔のカウント
        self.shoot_count = 0        # 手裏剣射出数カウント
        self.reload_count = 0       # 手裏剣の再装填カウント

    def hit_check(self, pos, r, anti_bullet=False, anti_shield=False):
        shuriken_list = []
        for shuriken in self.magazine:
            shuriken_list += shuriken.hit_check(pos, r, anti_bullet=anti_bullet)
        return shuriken_list

    def damage_process(self, damage):
        for shuriken in self.magazine:
            shuriken.damage_process(damage)

    def remove(self, shuriken):
        self.magazine.remove(shuriken)

    def update(self, stage:Stage):
        if self.reload_count>0:
            self.reload_count -= 1
            if self.reload_count==0:
                self.magazine.clear()
        # 投擲
        if self.status == "throw":
            # 投擲表現
            start_offset = Vector2(self.CONST.start_offset)
            if self.throw_direction == "right":
                throw_offset = Vector2(self.CONST.throw_offset)
            else:
                throw_offset = Vector2(-self.CONST.throw_offset[0], self.CONST.throw_offset[1])
            self.throwing.pos = (throw_offset-start_offset)*(self.throw_count/self.CONST.throw_time) + start_offset + self.user.pos
            self.throw_count += 1

            # 投げ終わりで射出
            if self.throw_count >= self.CONST.throw_time:
                self.throw_count = 0
                if self.throw_direction == "right":
                    self.throwing.shoot(Vector2(self.CONST.throw_speed_x, self.CONST.throw_speed_y))
                else:
                    self.throwing.shoot(Vector2(-self.CONST.throw_speed_x, self.CONST.throw_speed_y))
                self.throwing = None
                self.status = "wait"
                self.user.action_busy = False
                self.interval_count = self.CONST.interval
                self.shoot_count += 1
                if self.shoot_count >= self.CONST.shuriken_max:
                    self.shoot_count = 0
                    self.reload_count = self.CONST.reload
        elif self.interval_count>0:
            self.interval_count -= 1

        for shuriken in self.magazine:
            shuriken.update(stage)

    def throw_start(self):
        if self.reload_count==0 and self.status == "wait" and self.interval_count==0:
            self.status = "throw"
            #弾生成
            target = closest(self.user, self.user.target_list)
            if target==None:
                target=self.user
            self.throwing = Shuriken(user=self.user)
            self.magazine.append(self.throwing)
            self.user.action_busy = True
            # 射出処理
            self.throwing.pos = Vector2(self.CONST.start_offset) + self.user.pos
            # 射出方向は左右で判断
            # Xがターゲットの方が大きいなら右
            if target.pos.x>=self.user.pos.x:
                self.throw_direction = "right"
            # Xがターゲットの方が小さいなら左
            else:
                self.throw_direction = "left"



if __name__ == '__main__':
    temp = GameState()
    temp.add_character("red","6dfbf80a")
    temp.add_character("red","fb977406")
    temp.add_character("red","255ce79c")
    temp.add_character("green","d48bfad8")
    gs_list = [temp for i in range(8)]

    # ロールバックの処理負荷検討
    drone_set = InputHandler()
    drone_set.set_input(direction=Vector2(0,1), skills=[False,True,False], attack=False, shield=False)
    shoot_set = InputHandler()
    shoot_set.set_input(direction=Vector2(1,0), skills=[True,False,False], attack=False, shield=False)
    shoot_release = InputHandler()
    shoot_release.set_input(direction=Vector2(1,0), skills=[False,False,False], attack=False, shield=False)
    gs_list[-1].regist_input(drone_set, "6dfbf80a")
    gs_list[-1].regist_input(shoot_set, "fb977406")
    for i in range(16):
        gs_list[-1].update()
    gs_list[-1].regist_input(shoot_release, "fb977406")
    for i in range(2):
        gs_list[-1].update()
    pack_start = perf_counter()
    for state in gs_list:
        state.update()

    time = perf_counter()-pack_start
    print(f"1F update time:{time*1000:.3g}ms({time*64*100:.3g}%)")

    rollback_num = 8
    def fast_copy(x):
        import pickle
        return pickle.loads(pickle.dumps(x))
    pack_start = perf_counter()
    gs_list[(len(gs_list)-rollback_num):]=[fast_copy(gs_list[-1]) for i in range(rollback_num)]
    for i in range(rollback_num):
        for j in range(i):
            gs_list[i+len(gs_list)-rollback_num].update()
    time = perf_counter()-pack_start
    print(f"copy & update {rollback_num} state time:{time*1000:.3g}ms({time*64*100:.3g}%)")

