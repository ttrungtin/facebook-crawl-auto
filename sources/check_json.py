import os
import json
import sys
from shutil import copyfile

save = 'D:\\OneDrive - 광주과학기술원\\Project\\facebook\\filtered'
ori = 'D:\\OneDrive - 광주과학기술원\\Project\\facebook\\send'

j_dir = os.listdir('../send')
for j in j_dir:
	f_dir = os.path.join('../send',j)

	copy_dir = os.path.join(save, j)
	ori_dir = os.path.join(ori, j)
	try:
		with open(f_dir, encoding='utf-8') as f:
			data = json.load(f)
		copyfile(ori_dir, copy_dir)

	except:
		print(f_dir)
