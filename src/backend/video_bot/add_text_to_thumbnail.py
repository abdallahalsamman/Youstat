import sys, math, random, os
from PIL import Image, ImageFont, ImageDraw, ImageOps

text = sys.argv[2]
font_size = 150
fillcolor = "red"
shadowcolor = "yellow"
angle = random.randint(0,45)
directory = os.getcwd() + "/" + sys.argv[1]
output_directory = directory + "/" + "".join(x for x in text if x.isalnum())

if not os.path.exists(output_directory):
	os.mkdir(output_directory)
img_files = [file for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file)) and file.split(".")[-1] in ['png', 'jpg', 'jpeg']]

for img_file in img_files:
	try:
		img = Image.open(directory+img_file)
	except IOError as e:
		continue
	
	w, h = img.size
	font = ImageFont.truetype("video_bot/headline.regular.ttf", font_size)
	draw = ImageDraw.Draw(img)
	text_w, text_h = draw.textsize(text, font)
	text_w_n = int(abs(text_w * math.sin(angle)) + abs(text_h * math.cos(angle)))
	text_h_n = int(abs(text_w * math.cos(angle)) + abs(text_h * math.sin(angle)))

	txt=Image.new('RGBA', (text_w, text_h))
	d = ImageDraw.Draw(txt)
	d.text((-1, -1), text, font=font, fill=shadowcolor)
	d.text((+1, -1), text, font=font, fill=shadowcolor)
	d.text((-1, +1), text, font=font, fill=shadowcolor)
	d.text((+2, +1), text, font=font, fill=shadowcolor)
	d.text( (0, 0), text,  font=font, fill=fillcolor)
	txt_img=txt.rotate(angle,  expand=1)
	img.paste( 
		txt_img
		, (0, 0)
		, txt_img)
	img.save(output_directory +"/"+img_file.split('.')[0]+'-out.'+img_file.split('.')[-1])
print output_directory