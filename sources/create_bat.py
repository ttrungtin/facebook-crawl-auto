data_per_batch = 5
with open('run.bat', 'w') as file:
	file.write('(\n')
	for i in range(20):
		file.write('\tstart python main.py {} {}\n\ttimeout /t 5\n'.format(i*data_per_batch, '../logs/log_thread_{}.dat'.format(i)))
	file.write(')')


	# for i in range(20):
	# 	if i is not 19:
	# 		file.write('python main_fix.py {} {} && '.format(
	# 			i*50, 'log_thread_{}.dat'.format(i)))
	# 	else:
	# 		file.write('python main_fix.py {} {}'.format(
	# 			i*50, 'log_thread_{}.dat'.format(i)))
file.close()