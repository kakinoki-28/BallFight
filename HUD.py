import pygame, os

# ディレクトリパス
img_folder = "images"

def load_image(file):
    # 画像読み込み用
    file = os.path.join(img_folder, file)
    try:
        surface = pygame.image.load(file)
    except:
        raise SystemExit('Could not load image "%s" %s' % (file, pygame.get_error()))
    return surface

""" スキル用画像Surfaceを保持する辞書 """
skill_icons = {
    "energy_gun": load_image("liner_bullet.png"),
    "drone": load_image("drone.png"),
    "sync_shot": load_image("sync_bullet.png"),
    "knife": load_image("Knife.png"),
    "shuriken": load_image("Shuriken.png"),
    "warp": load_image("warp.png")
}

class SkillHUD:
    WIDTH = 240
    SLOT_GAP = 4
    SLOT_H = 30

    def __init__(self, x, y, icon_images=None):
        self.x = x
        self.y = y
        self.small_font = pygame.font.SysFont("consolas", 10, bold=True)
        #self.font = pygame.font.SysFont("consolas", 17, bold=True)
        self.font = pygame.font.Font(os.path.join("fonts","Makinas-4-Flat.otf"), 17)

    def draw(self, surface, character):
        skills = character.get_skills()

        # 240px幅に3つのスロットを配置
        slot_w = ( self.WIDTH - self.SLOT_GAP * (len(skills) - 1) ) // len(skills)

        for i, skill in enumerate(skills):
            rect = pygame.Rect( self.x + i * (slot_w + self.SLOT_GAP), self.y, slot_w, self.SLOT_H)
            self._draw_slot(surface, rect, skill, i)

    def _draw_slot(self, surface, rect, skill, index):
        pygame.draw.rect( surface, DARK_GRAY, rect, border_radius=5 )

        icon_rect = pygame.Rect( rect.x + 4, rect.y + 4, 20, 20 )
        if skill.name in skill_icons:
            image = pygame.transform.smoothscale(skill_icons.get(skill.name), (icon_rect.width, icon_rect.height))
            surface.blit(image, icon_rect)
        else:
            None  # スキルアイコンが見つからない場合は何も描画しない

        # スキルがワープの場合は残弾などは表示しない
        if skill.name == "warp":
            ready = self.small_font.render("READY", True, GREEN)
            surface.blit(
                ready,
                (rect.right - ready.get_width() - 4, rect.y + 2)
            )
            return

        # 残弾数
        ammo_text = self.font.render(
            f"{skill.shoot_count}/{skill.CONST.bullet_max}", True, WHITE
        )
        surface.blit(ammo_text, (rect.x + 35, rect.y + 10))

        # リロード演出
        if skill.reload_count > 0:
            self._draw_reload(surface, rect, skill)

        # 使用可能状態
        else:
            if not hasattr(skill, 'interval_count') or skill.interval_count <= 0:
                ready = self.small_font.render("READY", True, GREEN)
                surface.blit(
                    ready,
                    (rect.right - ready.get_width() - 4, rect.y + 2)
                )


    def _draw_reload(self, surface, rect, skill):
        # アイコン・スロット全体を暗くする
        overlay = pygame.Surface(
            (rect.width, rect.height), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 192))
        surface.blit(overlay, rect.topleft)

        # 下端のリロード進捗バー
        progress = 1.0 - skill.reload_count/skill.CONST.reload
        progress = max(0.0, min(1.0, progress))

        bar_rect = pygame.Rect(rect.x + 4, rect.bottom - 7, rect.width - 8, 3)
        pygame.draw.rect(surface, (70, 74, 86), bar_rect, border_radius=2)
        fill_rect = bar_rect.copy()
        fill_rect.width = int(bar_rect.width * progress)

        # リロード進捗バーを描画
        if fill_rect.width > 0:
            pygame.draw.rect(surface, YELLOW, fill_rect, border_radius=2)

        # 残り時間
        remaining = skill.reload_count/64
        time_text = self.font.render(
            f"{remaining:.1f}s", True, YELLOW
        )
        surface.blit(
            time_text,
            time_text.get_rect(center=(rect.centerx, rect.y + 12))
        )




class HP_Manager:
    def __init__(self, hp=200):
        # 実際のHP
        self.HP = self.MAX_HP = hp
        # 文字表示
        self.HP_text = self.HP
        self.tick_cnt_text = 0
        # ゲージ表示
        self.HP_level = self.HP
        self.wait_counter = 0

    def update(self, tick):
        # 文字表示の更新
        gap = abs(self.HP_text - self.HP)

        if gap>0:
            if 1<gap<=3:
                interval = 1/60
            elif 0<gap<=1:
                interval = 2/60
            else:
                interval = 1/120
        else:
            interval = -1

        if self.tick_cnt_text < interval:
            self.tick_cnt_text += tick/1000
        elif interval > 0:
            self.tick_cnt_text = 0
            if self.HP_text - self.HP>0:
                if gap>5:
                    self.HP_text -= 2
                else:
                    self.HP_text -= 1
            else:
                self.HP_text += 1

        # ゲージ表示の更新
        gap = abs(self.HP_level - self.HP)
        if gap>0:
            self.wait_counter += tick/1000
            # 減少待機
            if self.wait_counter>20/60:
                if self.HP_level - self.HP > 0:
                    self.HP_level -= tick/1000*100
                    if self.HP_level-self.HP<1:
                        self.HP_level = self.HP
                else:
                    self.HP_level += 1
        else:
            self.wait_counter = 0

class Enemy_HUD(HP_Manager):
    WIDTH = 240
    HEIGHT = 90 + 40
    def __init__(self, color="red"):
        super().__init__()
        self.color = color
        # フレーム
        self.surface = pygame.Surface((Enemy_HUD.WIDTH, Enemy_HUD.HEIGHT), flags = pygame.SRCALPHA).convert_alpha()
        self.back_image = load_image("enemy_hud.png").convert_alpha()
        self.change_color(color=color)
        self.skill_hud = SkillHUD(x=0, y=Enemy_HUD.HEIGHT-40)

    def change_color(self, color):
        # キャラクターアイコン
        self.character_image = pygame.transform.smoothscale(load_image(os.path.join("character", f"{color}.png")).convert_alpha(),(44,44))
        # HPバー
        self.hpbar_image = load_image(f"hpbar_{color}.png").convert_alpha()

    def make_surface(self, character):
        self.surface.fill((0,0,0,0))
        self.surface.blit(self.back_image, dest=(0,0))

        # キャラクターアイコン
        self.surface.blit(self.character_image, dest=(8,18))
        # HP文字表示
        HP_surface = Makinas_35.render(f"{self.HP_text}", True, WHITE)
        MAXHP_surface = Makinas_20.render(f"/{self.MAX_HP}", True, WHITE)
        self.surface.blit(HP_surface, dest=(Enemy_HUD.WIDTH-MAXHP_surface.get_width()-HP_surface.get_width(), 5))
        self.surface.blit(MAXHP_surface,dest=(Enemy_HUD.WIDTH-MAXHP_surface.get_width(), 5+5))
        # HPバー表示
        self.surface.blit(self.hpbar_image,dest=(60, 49), area=(0,0,int(160*self.HP/self.MAX_HP),20))
        # HP減少表示
        if self.HP_level-self.HP>0 and self.HP>=0:
            hp_dec_image = self.hpbar_image.copy()
            hp_dec_image.fill((0,144,144,0), special_flags = pygame.BLEND_RGBA_ADD)
            hp_dec_image.set_alpha(192)
            self.surface.blit(hp_dec_image,dest=(60+int(160*self.HP/self.MAX_HP), 49), area=(0,0,int(160*(self.HP_level-self.HP)/self.MAX_HP),20))
        # スキルHUD表示
        self.skill_hud.draw(self.surface, character)

    def update(self, tick, character):
        self.HP = character.hp
        super().update(tick)
        self.make_surface(character)


class Ally_HUD(HP_Manager):
    WIDTH = 240
    HEIGHT = 90
    def __init__(self, color="red"):
        super().__init__()
        self.color = color
        # フレーム
        self.surface = pygame.Surface((Enemy_HUD.WIDTH, Enemy_HUD.HEIGHT), flags = pygame.SRCALPHA).convert_alpha()
        self.change_color(color=color)

    def change_color(self, color):
        # キャラクターアイコン
        self.character_image = pygame.transform.smoothscale(load_image(os.path.join("character", f"{color}.png")).convert_alpha(),(44,44))
        # HPバー
        self.hpbar_image = load_image(f"hpbar_{color}.png").convert_alpha()

    def make_surface(self):
        self.surface.fill((0,0,0,0))
        self.surface.blit(self.back_image, dest=(0,0))

        # キャラクターアイコン
        self.surface.blit(self.character_image, dest=(8,18))
        # HP文字表示
        HP_surface = Makinas_35.render(f"{self.HP_text}", True, WHITE)
        MAXHP_surface = Makinas_20.render(f"/{self.MAX_HP}", True, WHITE)
        self.surface.blit(HP_surface, dest=(Enemy_HUD.WIDTH-MAXHP_surface.get_width()-HP_surface.get_width(), 5))
        self.surface.blit(MAXHP_surface,dest=(Enemy_HUD.WIDTH-MAXHP_surface.get_width(), 5+5))
        # HPバー表示
        self.surface.blit(self.hpbar_image,dest=(60, 49), area=(0,0,int(160*self.HP/self.MAX_HP),20))
        # HP減少表示
        if self.HP_level-self.HP>0 and self.HP>=0:
            hp_dec_image = self.hpbar_image.copy()
            hp_dec_image.fill((0,144,144,0), special_flags = pygame.BLEND_RGBA_ADD)
            hp_dec_image.set_alpha(192)
            self.surface.blit(hp_dec_image,dest=(60+int(160*self.HP/self.MAX_HP), 49), area=(0,0,int(160*(self.HP_level-self.HP)/self.MAX_HP),20))

    def update(self, tick, hp):
        self.HP = hp
        super().update(tick)
        self.make_surface()


# 定数定義
WIDTH = 1280
HEIGHT = 720
# カラーパレット
WHITE = (255,255,255)
LIGHT_GRAY = (192,192,192)
GRAY = (160,160,160)
DARK_GRAY = (64,64,64)
GRAY_224 = (224,224,224)
RED = (255,0,0)
GREEN = (32,224,64)
BLACK = (0,0,0)
CRIMSON = (220,20,60)
YELLOW = (245, 190, 75)
MUTED_BG = (155, 163, 179)

# フォント
pygame.init()
Makinas_35 = pygame.font.Font(os.path.join("fonts","Makinas-4-Flat.otf"), 35)
Makinas_20 = pygame.font.Font(os.path.join("fonts","Makinas-4-Flat.otf"), 20)

if __name__ == '__main__':

    run=True
    # Window定義
    WINDOW_SIZE = (WIDTH,HEIGHT)
    pygame.display.set_caption("SmashBalls!")
    window = pygame.display.set_mode(WINDOW_SIZE)
    # アセット定義
    background = load_image("universe_back.png").convert()
    stage = load_image("stage.png").convert_alpha()
    # フレームレート管理
    clock = pygame.time.Clock()
    FPS = 120

    y = HEIGHT/10

    PLAYER_NUM = 3
    HP_VALUE = 200
    HUD_LIST = [Enemy_HUD(color="red") for _ in range(PLAYER_NUM)]

    while run:
        # クロック処理
        tick = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if pygame.key.name(event.key) == "escape":
                    run = False
                elif pygame.key.name(event.key) == "0":
                    HP_VALUE += 10
                elif pygame.key.name(event.key) == "1":
                    HP_VALUE -= 40
                elif pygame.key.name(event.key) == "2":
                    HP_VALUE -= 20
        # 背景更新
        window.blit(background, (0,-80))
        pygame.draw.rect(window, GRAY, (0,HEIGHT-150,WIDTH,150))
        #window.blit(stage, (0, HEIGHT-100))

        #pygame.draw.line(window, WHITE, (0,y), (WIDTH,y), width = 1)
        for i in range(PLAYER_NUM):
            x = WIDTH/PLAYER_NUM*(i+1/2)
            HUD_LIST[i].update(tick, HP_VALUE)
            window.blit(HUD_LIST[i].surface,dest=(x-HUD_LIST[i].surface.get_width()/2,y-HUD_LIST[i].surface.get_height()/2))

        # 自機HUD
        
        pygame.draw.rect(window, GRAY_224, (WIDTH/2-160,HEIGHT-128,320,70))
        pygame.draw.rect(window, LIGHT_GRAY, (WIDTH/2-160,HEIGHT-58,400,48))
        pygame.draw.rect(window, LIGHT_GRAY, (WIDTH/2+160,HEIGHT-78,80,20))
        pygame.draw.rect(window, CRIMSON, (WIDTH/2-150,HEIGHT-48,300,28))
        pygame.draw.circle(window, LIGHT_GRAY, (WIDTH/2-180,HEIGHT-58), 30)
        char_image = pygame.transform.smoothscale(load_image(os.path.join("character", "red.png")).convert_alpha(),(44,44))
        window.blit(char_image, dest=(WIDTH/2-202,HEIGHT-80))
        for i in range(3):
            pygame.draw.rect(window, GRAY, (WIDTH/2-160+15+i*100,HEIGHT-118,90,50))
        

        
        """
        HP_surface1 = Makinas_50.render(f"{HP_1}", True, WHITE)
        x = WIDTH/4
        y = HEIGHT/8
        rx = x-HP_surface1.get_width()
        lx = x+MAXHP_surface.get_width()
        cy =y+int(HP_surface1.get_height()/2)-5
        if HP_1>0:
            pygame.draw.line(window, CRIMSON, (rx+int((lx-rx)*(200-HP_1)/200),cy), (lx,cy), width = 12)
        window.blit(HP_surface1, dest=(x-HP_surface1.get_width(), y-int(HP_surface1.get_height()/2)))
        window.blit(MAXHP_surface,dest=(x, y-int(HP_surface1.get_height()/2)+5))

        HP_surface2 = Makinas_50.render(f"{HP_2}", True, WHITE)
        x = WIDTH/4*3
        rx = x-HP_surface2.get_width()
        lx = x+MAXHP_surface.get_width()
        cy =y+int(HP_surface2.get_height()/2)-5
        if HP_2>0:
            pygame.draw.line(window, CRIMSON, (rx+int((lx-rx)*(200-HP_2)/200),cy), (lx,cy), width = 12)
        window.blit(HP_surface2, dest=(x-HP_surface2.get_width(), y-int(HP_surface2.get_height()/2)))
        window.blit(MAXHP_surface,dest=(x, y-int(HP_surface2.get_height()/2)+5))
        # グリッド
        #pygame.draw.line(window, RED, (x,0), (x,HEIGHT), width = 1)
        """


        # 画面更新
        pygame.display.update()
    pygame.quit()