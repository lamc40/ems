""" 图片验证码生成工具
生成一张带干扰线/点/圆圈的随机字母图片，返回 (PIL.Image, 验证码字符串)

用法：
    from app01.utils.check_code import check_code
    img, code_str = check_code()
    img.save('code.png')
"""
import random

from PIL import Image, ImageDraw, ImageFont, ImageFilter


def check_code(width=120, height=30, char_length=5, font_file='arial.ttf', font_size=28):
    """ 生成图片验证码
    :param width: 图片宽度
    :param height: 图片高度
    :param char_length: 验证码字符数
    :param font_file: 字体文件路径
    :param font_size: 字体大小
    :return: (PIL.Image, 验证码字符串)
    """
    code = []
    img = Image.new(mode='RGB', size=(width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img, mode='RGB')

    def rnd_char():
        """ 生成随机大写字母 """
        return chr(random.randint(65, 90))

    def rnd_color():
        """ 生成随机颜色（R较高避免太浅看不见） """
        return (random.randint(0, 255), random.randint(10, 255), random.randint(64, 255))

    # 写文字
    font = ImageFont.truetype(font_file, font_size)
    for i in range(char_length):
        char = rnd_char()
        code.append(char)
        h = random.randint(0, 4)
        draw.text([i * width / char_length, h], char, font=font, fill=rnd_color())

    # 写干扰点
    for i in range(40):
        draw.point([random.randint(0, width), random.randint(0, height)], fill=rnd_color())

    # 写干扰圆圈
    for i in range(40):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.arc((x, y, x + 4, y + 4), 0, 90, fill=rnd_color())

    # 画干扰线
    for i in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=rnd_color())

    img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
    return img, ''.join(code)


if __name__ == '__main__':
    img, code_str = check_code()
    print(code_str)
    with open('code.png', 'wb') as f:
        img.save(f, format='png')
