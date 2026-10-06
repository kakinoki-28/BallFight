from dataclasses import dataclass, field
from pygame import Vector2

""" 攻撃判定の定義 """
@dataclass
class Collision_Circle:
    rel_pos: Vector2 = field(default_factory=Vector2)     # 相対座標
    radius: int = 0                     # 攻撃判定の半径
    damage: int = 0                     # この判定のダメージ


""" 操作キャラクターの定数 """
@dataclass
class CharacterConst:
    radius: int = 30                # 当たり判定の半径
    hp_max: int = 200               # 最大体力

    speed_max: int = 5              # 最大速度
    friction: float = 0.3125        # 摩擦
    start_condition: float = 1.25   # 初速条件
    start_speed: float = 3.0        # 初速
    accelarate: float = 0.25        # 加速度

    next_jump_interval: int = 12    # (空中)ジャンプ入力の最小受付間隔
    normal_jump: int = 18           # 通常ジャンプの高さ
    air_jump: int = 15              # 空中ジャンプの高さ
    platform_jump: int = 15         # 台の上でのジャンプの高さ
    restrict_jump: int = 12         # 制限付き(シールドガード時の)ジャンプの高さ

    gravity: float = 1.0            # 重力
    grip_strong: float = 0.75       # 吹っ飛び時の強い空気抵抗(最大速度超過時)
    grip_weak: float = 0.5          # 吹っ飛び時の弱い空気抵抗(吹っ飛び直後)

    hopping_height: int = 40        # 跳ね時に動力を伝えられる最大高
    air_power: float = 0.125        # 跳ね・吹っ飛び時の動力

    drop_speed: int = 5             # 台からの飛び降り時の初速


""" シールドの定数 """
@dataclass
class ShieldConst:
    startup: int = 12               # 前隙のフレーム
    recovery: int = 16              # 後隙のフレーム
    instant_block: int = 6          # 直前ガード(対近接ガード)可能フレーム

    radius_max: int = CharacterConst.radius + 30    # ガード時の大きさ
    radius_first: int = 15                          # 開始時のガードの大きさ


""" 直進弾(LinerBullet)の定数 """
@dataclass
class LinerBulletConst:
    name: str = "liner_bullet"          # 弾の名前
    hp_max: int = 10                    # 弾の耐性
    radius: int = 10                    # 当たり判定の半径


    alive_frame: int = 40               # 弾が残るフレーム
    combo_interval: int = 0             # コンボ判定(ダメージ減算)が続くフレーム(0でコンボ無効)
    no_damage_frame: int = 16           # 当たったキャラが獲得する無敵フレーム
    hit_stop: int = 6                   # ヒットストップするフレーム
    shake: int = 8                      # ヒットストップ時振動する大きさ
    is_include_ratio: bool = True       # フレーム・振動計算時にダメージ量による変動するか
    damage: int = field(default_factory=int)    # 弾のダメージ(ダミー)

    hit_circles: list[Collision_Circle] = field(default_factory=list)

    def __post_init__(self):
        # 攻撃判定（相対位置、半径、ダメージ）を保存するリスト
        self.hit_circles = [ Collision_Circle(Vector2(0,0), 10, self.damage) ]


""" ハンマー(赤の近接攻撃)の定数 """
@dataclass
class HammerConst:
    interval: int = 16              # 次の入力が受け付けられるまでの間隔（フレーム）

    no_damage_frame: int = 96       # 受けたキャラが獲得する無敵フレーム
    after_blow_frame: int = 8       # 受けたキャラが吹っ飛び後空気抵抗が減少するフレーム

    """ キャラクターに対しての攻撃はダメージの倍率に応じてストップフレームが変動（柄ヒットは半分）
        ただし、ダメージが減少しても有利フレームが少なくならないように固定ストップフレームを設定 """
    hit_stop: int = 15              # 被攻撃時にヒットストップするフレーム
    self_hit_stop: int = 12         # 攻撃時にヒットストップするフレーム
    hit_const_stop: int = 4         # 被攻撃時に固定で追加ストップするフレーム
    shake: int = 15                 # 被攻撃時にストップ時振動する大きさ
    self_shake: int = 3             # 攻撃時にストップ時振動する大きさ

    shield_stop: int = 10           # シールド被攻撃時にヒットストップするフレーム
    self_shield_stop: int = 10      # シールド攻撃時にヒットストップするフレーム
    shield_const_stop: int = 8      # シールド被攻撃時に固定で追加ストップするフレーム
    shield_shake: int = 10          # シールド被攻撃時にストップ時振動する大きさ
    shield_self_shake: int = 3      # シールド攻撃時にストップ時振動する大きさ

    self_obj_stop: int = 6          # 他オブジェクトに当たった際のヒットストップ(固定)
    self_obj_shake: int = 3         # 他オブジェクトに当たった際の振動する大きさ

    blow_vector: Vector2 = field(default_factory=lambda: Vector2(21, 16))      # 受けたキャラが吹っ飛ばされる速度


    hit_circles: list[Collision_Circle] = field(default_factory=list)

    # フレーム毎のデータを保存するリスト
    frame_data: list[tuple[Vector2, int]] = field(default_factory=list)

    def __post_init__(self):
        # 攻撃判定（相対位置、半径、ダメージ）を保存するリスト
        self.hit_circles = [
            Collision_Circle(Vector2(0,88), 35, 40),
            Collision_Circle(Vector2(0,38), 15, 20)
        ]
        self.load_file()

    def load_file(self):
        with open("Hammer_data.txt") as f:
            self.startup, self.attacking, self.recovery = [int(value) for value in f.readline().rstrip('\n').split(',')]
            for line in f:
                value_list = [int(value) for value in line.rstrip('\n').split(',')]
                self.frame_data.append( (Vector2(value_list[0],value_list[1]), value_list[2]) )


""" エネルギー銃の「弾」の定数 """
@dataclass
class EnergyBulletConst(LinerBulletConst):
    name: str = "liner_bullet"          # 弾の名前
    hp_max: int = 10                    # 弾の耐性
    alive_frame: int = 40               # 弾が残るフレーム

    combo_interval: int = 0             # コンボ判定(ダメージ減算)が続くフレーム(0でコンボ無効)
    no_damage_frame: int = 16           # 当たったキャラが獲得する無敵フレーム
    hit_stop: int = 12                  # ヒットストップするフレーム
    shake: int = 12                     # ヒットストップ時振動する大きさ
    is_include_ratio: bool = True       # フレーム・振動計算時にダメージ量による変動するか

    hit_circles: list[Collision_Circle] = field(default_factory=list)

    def __post_init__(self):
        # 攻撃判定（相対位置、半径、ダメージ）を保存するリスト
        self.hit_circles = [
            Collision_Circle(Vector2(0,0), 10, self.damage)
        ]

""" エネルギー銃(EnerygyGun)の定数 """
@dataclass
class EnergyGunConst:
    startup: int = 12           # ボタンを押してから最短で弾が発射できるまでのフレーム
    charge: int = 24            # 最大チャージまでのフレーム
    interval: int = 16          # 弾が出る最短のフレーム
    reload: int = 96            # 弾の装填にかかるフレーム

    bullet_max: int = 7         # 1マガジンで撃てる最大の弾

    angle_range_max: int = 15   # 溜めない状態でブレる角度の最大値
    angle_range_min: int = 1    # 最大溜め状態でブレる角度の最大値
    speed_min: int = 12         # 溜めない状態の速度
    speed_max: int = 25         # 最大溜め状態の速度
    damage_min: int = 5         # 溜めない状態のダメージ
    damage_max: int = 20        # 最大溜め状態のダメージ
    alive_min: int = 20         # 溜めない状態で弾が残るフレーム
    alive_max: int = 40         # 最大溜め状態で弾が残るフレーム

    rotate_speed: float = 360/64    # 照準を合わせる角速度


""" ドローン本体の定数 """
@dataclass
class DroneConst:
    hp_max: int = 5             # 弾の耐性
    alive_frame: int = 320      # 弾が残るフレーム
    startup: int = 24           # 追尾し始めるまでのフレーム
    homing_interval: int = 4    # 追尾ベクトルを更新するフレーム

    speed_max: int = 10         # 追尾時の最大速度　及び　射出時の固定速度

    no_damage_frame: int = 24   # 当たったキャラが取得する無敵フレーム
    hit_stop: int = 8           # 当たったキャラがヒットストップするフレーム
    shake: int = 5              # 当たったキャラのヒット振動の大きさ

    hit_circles: list[Collision_Circle] = field(default_factory=list)

    def __post_init__(self):
        # 攻撃判定（相対位置、半径、ダメージ）を保存するリスト
        self.hit_circles = [
            Collision_Circle(Vector2(0,0), 15, 15)
        ]

""" ドローン管理の定数 """
@dataclass
class DroneManagerConst:
    throw_time: int = 24        # 射出にかかるフレーム
    angle_range: int = 25       # 射出角度の幅
    interval: int = 24          # ドローン射出から次のドローンまでの間隔
    reload: int = 320           # 再装填フレーム

    drone_max: int = 4          # ドローン最大数


""" 時止め弾の「弾」の定数 """
@dataclass
class SyncBulletConst(LinerBulletConst):
    name: str = "sync_bullet"           # 弾の名前
    hp_max: int = 10                    # 弾の耐性
    alive_frame: int = 60               # 弾が残るフレーム

    speed: int = 24                     # 弾のスピード

    combo_interval: int = 8             # コンボ判定(ダメージ減算)が続くフレーム(0でコンボ無効)
    no_damage_frame: int = 16           # 当たったキャラが獲得する無敵フレーム
    hit_stop: int = 4                   # ヒットストップするフレーム
    shake: int = 12                     # ヒットストップ時振動する大きさ
    is_include_ratio: bool = True       # フレーム・振動計算時にダメージ量による変動するか
    damage: int = 20                    # 弾が与えるダメージ

    hit_circles: list[Collision_Circle] = field(default_factory=list)

    def __post_init__(self):
        # 攻撃判定（相対位置、半径、ダメージ）を保存するリスト
        self.hit_circles = [
            Collision_Circle(Vector2(0,0), 10, self.damage)
        ]

""" 時止め弾管理の定数 """
@dataclass
class SyncShooterConst:
    reload: int = 320           # 再装填までのフレーム
    bullet_max: int = 4         # 弾の最大数（+1回目の入力で発射）


""" クナイの「弾」の定数 """
@dataclass
class KnifeBulletConst(LinerBulletConst):
    name: str = "knife_bullet"           # 弾の名前
    hp_max: int = 10                    # 弾の耐性
    alive_frame: int = 60               # 弾が残るフレーム

    speed: int = 24                     # 弾のスピード

    combo_interval: int = 0             # コンボ判定(ダメージ減算)が続くフレーム(0でコンボ無効)
    no_damage_frame: int = 16           # 当たったキャラが獲得する無敵フレーム
    hit_stop: int = 16                  # ヒットストップするフレーム
    shake: int = 16                     # ヒットストップ時振動する大きさ
    is_include_ratio: bool = True       # フレーム・振動計算時にダメージ量による変動するか
    damage: int = 20                    # 弾が与えるダメージ

    hit_circles: list[Collision_Circle] = field(default_factory=list)

    def __post_init__(self):
        # 攻撃判定（相対位置、半径、ダメージ）を保存するリスト
        self.hit_circles = [
            Collision_Circle(Vector2(0,0), 10, self.damage)
        ]


""" クナイ管理の定数 """
@dataclass
class KnifeManagerConst:
    throw_time: int = 12        # 射出にかかるフレーム
    angle_range: int = 5       # 射出角度の幅
    interval: int = 24          # ドローン射出から次のドローンまでの間隔

    reload: int = 192           # 再装填までのフレーム
    bullet_max: int = 4         # 弾の最大数

def debug():
    CONST = EnergyBulletConst(damage=10)
    print(CONST)

if __name__ == '__main__':
    debug()