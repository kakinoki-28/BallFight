import pygame
from dataclasses import dataclass, field
import os
import math
from random import randint
import gamelogic
import HUD
import pygame.gfxdraw

IMAGE_FOLDER = "images"

SILVER = (192, 192, 192)

def load_image(file):
    # 画像読み込み用
    file = os.path.join(IMAGE_FOLDER, file)
    try:
        surface = pygame.image.load(file)
    except:
        raise SystemExit('Could not load image "%s" %s' % (file, pygame.get_error()))
    return surface

""" おうぎ形を描画する関数 """
def draw_pie(screen, color, pos, radius, angle, angle_range):
    p=[pos]
    for n in range(angle-angle_range,angle+angle_range):
        x = pos[0]+round(radius*math.sin(n*math.pi/180))
        y = pos[1]-round(radius*math.cos(n*math.pi/180))
        p.append((x, y))
    pygame.gfxdraw.filled_polygon(screen, p, color)
    pygame.gfxdraw.aapolygon(screen, p, color)

""" 矢印を描画する関数 """
def draw_arrow(screen, color, start_pos, arrow, width):
    total_length = arrow.length()
    # ゼロベクトルなら描画しない
    if total_length == 0:
        return
    # y軸が下向きの座標系に合わせるため、矢印のy成分を反転
    arrow.y *= -1
    # 方向ベクトル
    direction = arrow.normalize()

    # 矢印頭部のサイズ
    head_length = width * 3     # 矢印の頭の長さ
    head_width = width * 2.5    # 矢印の頭の横幅
    # 矢印の頭部が矢印の長さより長くならないように調整
    if head_length > total_length/2:
        head_length = total_length/2

    # 各種基準点の計算
    end_pos = start_pos + arrow                     # 矢印の先端座標
    head_base = end_pos - direction * head_length   # 矢印の頭の基準点座標
    # 法線ベクトル
    normal_vector = direction.rotate(90)
    # 各頂点の座標を計算
    shaft_top_left = head_base - normal_vector * (width / 2)
    shaft_top_right = head_base + normal_vector * (width / 2)
    shaft_bottom_left = start_pos - normal_vector * (width / 2)
    shaft_bottom_right = start_pos + normal_vector * (width / 2)

    head_top = end_pos
    head_btm_right = head_base + normal_vector * (head_width / 2)
    head_btm_left = head_base - normal_vector * (head_width / 2)

    p = [
        shaft_bottom_left,
        shaft_top_left,
        head_btm_left,
        head_top,
        head_btm_right,
        shaft_top_right,
        shaft_bottom_right,
    ]

    pygame.gfxdraw.filled_polygon(screen, p, color)
    pygame.gfxdraw.aapolygon(screen, p, color)


""" 画像Surfaceを保持するクラス """
@dataclass
class ImageAssets:
    stage: dict[str, pygame.Surface] = field(default_factory=dict)      # ステージの画像を保持する辞書
    character: dict[str, pygame.Surface] = field(default_factory=dict)  # キャラクターの画像を保持する辞書
    shield: dict[str, pygame.Surface] = field(default_factory=dict)     # シールドの画像
    melee: dict[str, pygame.Surface] = field(default_factory=dict)      # 近接攻撃の画像を保持する辞書
    bullet: dict[str, pygame.Surface] = field(default_factory=dict)     # キャラが使用する弾の画像を保持する辞書
    effect: dict[str, pygame.Surface] = field(default_factory=dict)     # エフェクトの画像を保持する辞書

    def __post_init__(self):
        # 画像の読み込み
        self.stage = {
            "background": load_image("universe_back.png").convert(),
            "stage": load_image("stage.png").convert(),
            "platform": load_image("platform.png").convert_alpha()
        }
        self.character = {
            "red": load_image(os.path.join("character", "red.png")).convert_alpha(),
            "green": load_image(os.path.join("character", "green.png")).convert_alpha()
        }
        self.shield = {
            "default": load_image("shield.png").convert_alpha()
        }
        self.melee = {
            "hammer": load_image("hammer.png").convert_alpha()
        }
        self.bullet = {
            "liner_bullet": load_image("liner_bullet.png").convert_alpha(),
            "drone": load_image("drone.png").convert_alpha(),
            "sync_bullet": load_image("sync_bullet.png").convert_alpha(),
            "knife_bullet": load_image("Knife.png").convert_alpha(),
        }
        self.effect = {
            "airjump": load_image("airjump.png").convert_alpha()
        }

def blit_center(dest, source, pos):
    # 画像を中心に描画するための関数
    rect = source.get_rect(center=pos)
    dest.blit(source, rect)

class GameRenderer:
    def __init__(self):
        self.screen = pygame.Surface((gamelogic.Stage.WIDTH, gamelogic.Stage.HEIGHT)).convert_alpha() 
        self.image_assets = ImageAssets()
        self.HUD_LIST = {}
        self.debug_mode = False

    def debug_toggle(self):
        self.debug_mode = not self.debug_mode

    """ 各オブジェクトの速度ベクトルを描画する関数（デバッグ用）"""
    def draw_speed(self, target):
        if target.speed.length() > 0:
            #speed = target.speed.copy()
            #draw_arrow(self.screen, SILVER, pygame.Vector2(target.pos.x, self.screen.get_height()-target.pos.y), speed*4, 5)
            x_only = pygame.Vector2(target.speed.x, 0)
            y_only = pygame.Vector2(0, target.speed.y)
            draw_arrow(self.screen, (192,192,192,192), pygame.Vector2(target.pos.x, self.screen.get_height()-target.pos.y), x_only*4, 5)
            draw_arrow(self.screen, (192,192,192,192), pygame.Vector2(target.pos.x, self.screen.get_height()-target.pos.y), y_only*4, 5)

    """ 毎フレーム描画する関数 """
    def render(self, window, tick, game_state):
        # 背景の描画
        self.screen.blit(self.image_assets.stage["background"], (0, 0))
        # ステージの描画
        self.screen.blit(self.image_assets.stage["stage"], (0, self.screen.get_height()-game_state.stage.GND_HEIGHT))
        # 台の描画
        for platform in game_state.stage.platforms:
            self.screen.blit(self.image_assets.stage["platform"], (platform.x[0], self.screen.get_height()-platform.y))
        
        # HUDの描画
        TOTAL_PLAYER = len(game_state.characters_list) 
        if TOTAL_PLAYER!=len(self.HUD_LIST.keys()):
            self.HUD_LIST = {}
            for chara in game_state.characters_list:
                self.HUD_LIST[chara.id] = HUD.Enemy_HUD(color=chara.color)
        for i, (chara_id, hud) in enumerate(self.HUD_LIST.items()):
            x = game_state.stage.WIDTH/TOTAL_PLAYER*(i+1/2)
            y = game_state.stage.HEIGHT/10
            for chara in [_ for _ in game_state.characters_list if _.id == chara_id]:
                hud.update(tick, chara.hp)
                self.screen.blit(hud.surface,dest=(x-hud.surface.get_width()/2,y-hud.surface.get_height()/2))

        
        # エフェクト表示
        for chara in game_state.characters_list:
            for effect in chara.effects:
                effect_image = self.image_assets.effect[effect.name].copy()
                # エフェクト別処理
                if effect.name == "airjump":
                    effect_image = pygame.transform.smoothscale(effect_image, (20+int(4*effect.count), 8+int(effect.count/2)))
                    if effect.count >= 4:
                        effect_image.set_alpha(255-int(240*(effect.count-4)/6))
                    else:
                        effect_image.set_alpha(255)
                self.screen.blit(effect_image, dest=(effect.pos.x-int(effect_image.get_width()/2), self.screen.get_height()-effect.pos.y-int(effect_image.get_height()/2)))


        # キャラクターの描画
        for chara in game_state.characters_list:
            chara_image = self.image_assets.character[chara.color].copy()
            # 無敵時の点滅処理
            if chara.no_damage_count>0:
                ratio = 1-abs(chara.no_damage_count%33-16)/16
                if ratio > 0:
                    white_level = int(128*ratio/2+64)
                    chara_image.fill((white_level, white_level, white_level, 0), special_flags = pygame.BLEND_RGBA_ADD)
            # キャラの描画（ヒット時振動あり）
            X, Y = round(chara.pos + chara.shake_offset)
            blit_center(self.screen, chara_image, (X, self.screen.get_height()-Y))

            # シールド
            if chara.shield.status != "wait":
                shield_image = self.image_assets.shield["default"].copy()
                if chara.shield.radius*2 != shield_image.get_width():
                    shield_image = pygame.transform.smoothscale(shield_image, (chara.shield.radius*2,)*2)
                blit_center(self.screen, shield_image, (X, self.screen.get_height()-Y))

            # 速度ベクトルの描画（デバッグモード）
            if self.debug_mode:
                self.draw_speed(chara)

        # 攻撃系の描画
        for chara in game_state.characters_list:
            # 反射した弾の描画
            for bullet in chara.shield.hitback_bullets:
                if bullet.display:
                    blit_center(self.screen, self.image_assets.bullet[bullet.CONST.name], (bullet.pos.x, self.screen.get_height()-bullet.pos.y))
                    # 速度ベクトルの描画（デバッグモード）
                    if self.debug_mode:
                        self.draw_speed(bullet)

            if chara.color == "red":
                # 近接攻撃の描画
                if chara.hammer.active:
                    hammer_image = self.image_assets.melee["hammer"].copy()
                    if chara.hammer.angle != 0:
                        hammer_image = pygame.transform.rotozoom(hammer_image, -chara.hammer.angle, 1)
                    root_pos = chara.pos+chara.hammer.offset
                    if chara.hammer.motion == "attack":
                        if chara.hammer.direction == "left":
                            root_pos.x -= (1-chara.hammer.distance_ratio)*(chara.hammer.offset.x + chara.hammer.CONST.frame_data[chara.hammer.motion_count-1][0].x)
                        else:
                            root_pos.x -= (1-chara.hammer.distance_ratio)*(chara.hammer.offset.x - chara.hammer.CONST.frame_data[chara.hammer.motion_count-1][0].x)
                        root_pos.y -= (1-chara.hammer.distance_ratio)*(chara.hammer.offset.y - chara.hammer.CONST.frame_data[chara.hammer.motion_count-1][0].y)
                    hammer_pos = round( root_pos+pygame.Vector2(0, hammer_image.get_height()//2).rotate(-chara.hammer.angle) )
                    
                    blit_center(self.screen, hammer_image, (hammer_pos.x, self.screen.get_height()-hammer_pos.y))


                # スキル1:エネルギーガン
                if not (chara.energy_gun.status == "wait" or chara.energy_gun.status == "wait_interval"):
                    draw_pie(self.screen, SILVER, (chara.pos.x, self.screen.get_height()-chara.pos.y), 
                             40+10*chara.energy_gun.charge_count/chara.energy_gun.CONST.charge, 
                             round(chara.energy_gun.angle), round(chara.energy_gun.angle_range))
                for bullet in chara.energy_gun.magazine:
                    if bullet.display:
                        blit_center(self.screen, self.image_assets.bullet[bullet.CONST.name], (bullet.pos.x, self.screen.get_height()-bullet.pos.y))
                        # 速度ベクトルの描画（デバッグモード）
                        if self.debug_mode:
                            self.draw_speed(bullet)
                # スキル2:ドローン
                for drone in chara.drone.magazine:
                    if drone.active or drone.wait:
                        blit_center(self.screen, self.image_assets.bullet["drone"], (drone.pos.x, self.screen.get_height()-drone.pos.y))
                        # 速度ベクトルの描画（デバッグモード）
                        if self.debug_mode:
                            self.draw_speed(drone)
                # スキル3:時止め弾
                for bullet in chara.sync_shot.magazine:
                    if bullet.display:
                        blit_center(self.screen, self.image_assets.bullet[bullet.CONST.name], (bullet.pos.x, self.screen.get_height()-bullet.pos.y))
                        # 速度ベクトルの描画（デバッグモード）
                        if self.debug_mode:
                            self.draw_speed(bullet)
            # 緑キャラの描画
            elif chara.color == "green":
                # スキル1:クナイ
                for knife in chara.knife.magazine:
                    if knife.display:
                        # 回転させて描画
                        # 投擲中なら、位置関係から回転を算出
                        if knife.shoot_wait:
                            angle = pygame.Vector2(-1,0).angle_to((knife.pos-chara.pos).rotate(90))
                            knife_image = pygame.transform.rotozoom(self.image_assets.bullet["knife_bullet"].copy(), angle, 1)
                        # 動作中なら、速度方向から回転を算出
                        else:
                            angle = pygame.Vector2(-1,0).angle_to(knife.speed)
                            knife_image = pygame.transform.rotozoom(self.image_assets.bullet["knife_bullet"].copy(), angle, 1)

                        blit_center(self.screen, knife_image, (knife.pos.x, self.screen.get_height()-knife.pos.y))

                        # 速度ベクトルの描画（デバッグモード）
                        if self.debug_mode:
                            self.draw_speed(knife)

        # 描画の反映
        window.blit(self.screen, (0, 0))
