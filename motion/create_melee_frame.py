import os


""" 近接攻撃のフレームデータを作成する """
if __name__ == "__main__":
    # 作成する近接攻撃の名前とフレーム数
    Name = "Katana"
    startup = 24
    attack = 15
    recovery = 18

    # キーフレームの座標と角度
    point = [[15,0],[60,10],[10,90],[-60,40],[0,0],[30,0]]
    angle = [270, 255, 180, 90, 0, -90]
    # 画像の反転フラグ(Trueで反転) キーフレーム間の補間用なので１つ少ない
    flip = [True, True, True, True, True]

    # キーフレームから線形補間してフレームデータを作成する
    if not os.path.isdir("motion"):
        dirname = os.path.dirname(__file__)
    else:
        dirname = "motion"
    with open(os.path.join(dirname, Name+"_data.txt"),"w", encoding='utf-8') as f:
        f.write(str(startup)+","+str(attack)+","+str(recovery)+"\n")
        # 線形補間
        for t in range(startup+attack+recovery+1):
            if t<startup*3/4:
                ratio = 1/(startup*3/4)*t
                offset = [point[0][_] + (point[1][_]-point[0][_])*ratio for _ in range(2)]
                theta = angle[0] + (angle[1]-angle[0])*ratio
                image_flip = flip[0]
            # 溜め
            elif t<startup:
                offset = point[1]
                theta = angle[1]
                image_flip = flip[0]
            elif t<startup+attack/3:
                ratio = 1/(attack/3)*(t-startup)
                offset = [point[1][_] + (point[2][_]-point[1][_])*ratio for _ in range(2)]
                theta = angle[1] + (angle[2]-angle[1])*ratio
                image_flip = flip[1]
            elif t<startup+attack*2/3:
                ratio = 1/(attack/3)*(t-startup-attack/3)
                offset = [point[2][_] + (point[3][_]-point[2][_])*ratio for _ in range(2)]
                theta = angle[2] + (angle[3]-angle[2])*ratio
                image_flip = flip[2]
            elif t<startup+attack:
                ratio = 1/(attack/3)*(t-startup-attack*2/3)
                offset = [point[3][_] + (point[4][_]-point[3][_])*ratio for _ in range(2)]
                theta = angle[3] + (angle[4]-angle[3])*ratio
                image_flip = flip[3]
            else:
                ratio = 1/recovery*(t-startup-attack)
                offset = [point[4][_] + (point[5][_]-point[4][_])*ratio for _ in range(2)]
                theta = angle[4] + (angle[5]-angle[4])*ratio
                image_flip = flip[4]
            offset =[int(_) for _ in offset]
            theta = int(theta)
            image_flip = int(image_flip)
            line = str(offset[0])+","+str(offset[1])+","+str(theta)+","+str(image_flip)
            print(line)
            f.write(line+"\n")
