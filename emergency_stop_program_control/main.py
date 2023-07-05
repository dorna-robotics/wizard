import time
import queue
import subprocess
import psutil
import os
import signal
from dorna2 import Dorna
import config

def kill_process_and_children(pid):
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            os.kill(child.pid, signal.SIGKILL)
        os.kill(pid, signal.SIGKILL)
    except psutil.NoSuchProcess:
        print(f"No process with PID {pid} found.")
    except psutil.AccessDenied:
        print(f"Access denied to process with PID {pid}.")
    except Exception as e:
        print(f"Error occurred while terminating process and its children: {e}")


def start_event(msg, union, robot):
	# check the start condition
	if robot.prm_config.emergency_key not None and robot.prm_config.emergency_value is not None and robot.prm_config.emergency_key in msg and msg[robot.prm_config.emergency_key] != robot.prm_config.emergency_value:

		# check the queue
		try:
			# only one thread gets here
			robot.prm_file_start.get(False)

			# clear the alarm
			robot.set_alarm(0)
			
			# run the items
			for file in robot.prm_config.file_list:
				filename = os.path.basename(file)
				filename_without_extension = os.path.splitext(filename)[0]
				dirname = os.path.dirname(file)
				
				# run
				result = subprocess.Popen("cd "+dirname+ " && sudo python3 "+filename_without_extension+".py", shell=True)
				#result = subprocess.Popen("cd "+dirname+ " && python "+filename_without_extension+".py", shell=True)

				# Get the PID of the subprocess using the PID of the completed process
				robot.prm_pid.append(result.pid)


			# clear the start event
			robot.clear_event(start_event)

			# add the terminate event
			robot.prm_file_terminate.put(0)
			robot.add_event(target=terminate_event, kwargs={"robot": robot})

		except Exception as ex:
			print(ex)

def terminate_event(msg, union, robot):
	# check the terminate condition
	if robot.prm_config.emergency_key is not None and robot.prm_config.emergency_value is not None and robot.prm_config.emergency_key in msg and msg[robot.prm_config.emergency_key] == robot.prm_config.emergency_value:
		
		# check the queue
		try:
			# only one thread gets here
			robot.prm_file_terminate.get(False)
			
			# terminate the pids
			while robot.prm_pid:
				pid = robot.prm_pid.pop()
				kill_process_and_children(pid)
				#os.kill(pid, signal.SIGKILL)
				#subprocess.Popen("taskkill /F /PID "+str(pid), shell=True)


			# clear the start event
			robot.clear_event(terminate_event)

			# add the terminate event
			robot.prm_file_start.put(0)
			robot.add_event(target=start_event, kwargs={"robot": robot})

		except Exception as ex:
			print(ex)


def main(robot):
	# register an stop function
	robot.add_event(target=start_event, kwargs={"robot": robot})

	# main loop
	while True:
		robot.get_input(0)
		time.sleep(10)


if __name__ == '__main__':
	robot = Dorna()

	# init
	robot.prm_config = config
	robot.prm_file_start = queue.Queue()
	robot.prm_file_start.put(0)
	robot.prm_file_terminate = queue.Queue()
	robot.prm_pid = []

	# connect to the robot
	if robot.connect(robot.prm_config.ip):
		main(robot)
	
	# close the connection
	robot.close()