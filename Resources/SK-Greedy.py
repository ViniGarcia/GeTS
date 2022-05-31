############################################# SK-GREEDY TRANSMISSION SCHEDULER - GeTS ###############################################

import statistics
import random
import time
import numpy
import copy
import math
import sys

#########################################################################################################################################
#################################################### SK-GREEDY STRATEGY - RESOURCES #####################################################
#########################################################################################################################################

class SINR:

	__alfa = None
	__sinr_threshold_db = None
	__sinr_adjust_db = None
	__no_dbm = None

	__sinr_threshold = None
	__sinr_adjust = None

	__devices_map = None
	__devices_closiest = None
	__transmission_power = None
	__interference_power = None
	__interference_limits = None

	__taboo_list = None
	__slot_maximum = None

	def __init__(self, alfa, sinr_threshold_db, sinr_adjust_db, no_dbm, slot_maximum):
		
		self.__alfa = alfa
		self.__sinr_threshold_db = sinr_threshold_db
		self.__sinr_adjust_db = sinr_adjust_db
		self.__no_dbm = no_dbm

		self.__sinr_threshold = 10**(self.__sinr_threshold_db/10)
		self.__sinr_adjust = 10**(self.__sinr_adjust_db/10)
		self.__no_mw = 10**(self.__no_dbm/10)
		self.__no_w = self.__no_mw * 10**(-3)

		self.__slot_maximum = slot_maximum
		self.__taboo_list = [[] for cs in range(slot_maximum)]


	def __coordinatesMatrix(self, devices_coordinate):

		devices_matrix = []
		for i in range(len(devices_coordinate)):
			matrix_line = []
			for j in range(len(devices_coordinate)):
				matrix_line.append(math.sqrt((devices_coordinate[i][0] - devices_coordinate[j][0]) **2 + (devices_coordinate[i][1] - devices_coordinate[j][1])**2))
			devices_matrix.append(matrix_line)

		return devices_matrix

	
	def devices(self):

		return list(range(len(self.__devices_map)))


	def reset(self):

		self.__taboo_list = [[] for cs in range(self.__slot_maximum)]


	def prepare(self, devices_file_path):

		devices_file = open(devices_file_path)
		devices_coordinate = []
		for device_raw in devices_file:
			device_line = device_raw.split()
			devices_coordinate.append((int(device_line[0]), int(device_line[1])))
		devices_file.close()

		self.__devices_map = self.__coordinatesMatrix(devices_coordinate)

		self.__transmission_power = []
		self.__devices_closiest = [-1] * len(devices_coordinate)
		devices_distances = [sys.maxsize] * len(devices_coordinate)
		for i in range(len(devices_coordinate)):
			for j in range(i+1, len(devices_coordinate)):
				
				if self.__devices_map[i][j] < devices_distances[i]:
					devices_distances[i] = self.__devices_map[i][j]
					self.__devices_closiest[i] = j

				if self.__devices_map[j][i] < devices_distances[j]:
					devices_distances[j] = self.__devices_map[j][i]
					self.__devices_closiest[j] = i

			self.__transmission_power.append((self.__sinr_threshold + self.__sinr_adjust) * self.__no_w * self.__devices_map[i][self.__devices_closiest[i]] ** self.__alfa)

		self.__interference_power = numpy.zeros((len(devices_coordinate), len(devices_coordinate)))
		self.__interference_limits = []
		for i in range(len(devices_coordinate)):
			for k in range(i+1, len(devices_coordinate)):
				
				if k != self.__devices_closiest[i]:
					self.__interference_power[i][k] = self.__transmission_power[k] / self.__devices_map[k][self.__devices_closiest[i]] ** self.__alfa
				if i != self.__devices_closiest[k]:
					self.__interference_power[k][i] = self.__transmission_power[i] / self.__devices_map[i][self.__devices_closiest[k]] ** self.__alfa

			self.__interference_limits.append(((self.__transmission_power[i] / self.__devices_map[i][self.__devices_closiest[i]] ** self.__alfa) - self.__sinr_threshold * self.__no_w) / self.__sinr_threshold)


	def check(self, devices_slot):

		if devices_slot in self.__taboo_list[len(devices_slot)-1]:
			return False

		for main_transmitter in devices_slot:
			interference_sum = 0

			for co_transmitter in devices_slot:

				if co_transmitter == self.__devices_closiest[main_transmitter]:
					self.__taboo_list[len(devices_slot)-1].append(devices_slot)
					return False
				if(main_transmitter != co_transmitter):
					interference_sum += self.__interference_power[main_transmitter][co_transmitter]

			if(interference_sum >= self.__interference_limits[main_transmitter]):
				self.__taboo_list[len(devices_slot)-1].append(devices_slot)
				return False
	
		return True

#--

class stochasticKGreedyScheduler:

	__slot_maximum = None
	__stochastic_k = None
	__sinr_manager = None


	def __init__(self, slot_maximum, stochastic_k, sinr_manager):

		self.__slot_maximum = slot_maximum
		self.__stochastic_k = stochastic_k
		self.__sinr_manager = sinr_manager

		self.__device_list = self.__sinr_manager.devices()


	def __generateSlot(self, device_sublist):

		slot_candidate = [device_sublist.pop(0)]
		slot_sublist = copy.copy(device_sublist)
		
		for attempts in range(self.__slot_maximum):
			if len(slot_candidate) == self.__slot_maximum:
				break
			
			if len(slot_sublist) > self.__stochastic_k:
				slot_devices = random.sample(slot_sublist, self.__stochastic_k)
			else:
				slot_devices = copy.copy(slot_sublist)

			for index in range(len(slot_devices)):
				slot_candidate.append(slot_devices.pop(0))
				if self.__sinr_manager.check(slot_candidate):
					slot_sublist.remove(slot_candidate[-1])
					device_sublist.remove(slot_candidate[-1])
					break
				else:
					slot_sublist.remove(slot_candidate.pop())
			
		return slot_candidate


	def __generate(self):

		device_sublist = copy.copy(self.__device_list)
		stdma_candidate = []
		while len(device_sublist) > 0:
			stdma_candidate.append(self.__generateSlot(device_sublist))

		return stdma_candidate


	def executeByTime(self, seconds):

		generated_candidates = []

		end_time = time.time() + seconds
		while time.time() < end_time:
			generated_candidates.append(self.__generate())

		generated_candidates.sort(key = len)
		return generated_candidates


	def executeByGenerations(self, rounds):

		generated_candidates = []

		for r in range(rounds):
			generated_candidates.append(self.__generate())

		generated_candidates.sort(key = len)
		return generated_candidates


	def simpleExecution(self, mode, generations=500, seconds=5):

		initial_time = time.time()
		if mode == "g":
			results = self.executeByGenerations(generations)
		elif mode == "s":
			results = self.executeByTime(seconds)
		else:
			print("\nINVALID EXECUTION MODE!")
			return
		final_time = time.time()

		if len(results) > 10:
			top10 = results[:10]
		else:
			top10 = results

		top10_eval = [len(candidate) for candidate in top10]
		general_eval = [len(candidate) for candidate in results]

		print("\n================= EXECUTION BEGIN ================")
		print("\n--")
		print("BEST SCHEDULE FOUND:", results[0])
		print("BEST SCHEDULE SIZE:", len(results[0]))
		print("--")
		print("TOP " + str(len(top10)) + " SCHEDULES STATISTICS:")
		print("\tMEAN SCHEDULE SIZE:", statistics.mean(top10_eval))
		print("\tSTDEV SCHEDULE SIZE:", statistics.stdev(top10_eval))
		print("--")
		print("LAST GENERATION STATISTICS:")
		print("\tMEAN SCHEDULE SIZE:", statistics.mean(general_eval))
		print("\tSTDEV SCHEDULE SIZE:", statistics.stdev(general_eval))
		print("--")
		print("EXECUTION TIME (s):", final_time - initial_time)
		print("--\n")
		print("==================================================\n")


	def experimentExecution(self, rounds, mode, generations=500, seconds=5):

		if type(rounds) != int or rounds < 2:
			print("\nINAVLID NUMBER OF ROUNDS!")
			return

		time_eval = []
		best_eval = []
		print("\n================ EXPERIMENT BEGIN ================\n")
		for r in range(rounds):
			self.__sinr_manager.reset()
			print("STARTING ROUND #" + str(r+1) + "!")
			initial_time = time.time()
			if mode == "g":
				results = self.executeByGenerations(generations)
			elif mode == "s":
				results = self.executeByTime(seconds)
			else:
				print("\nINVALID EXECUTION MODE!")
				return
			final_time = time.time()

			time_eval.append(final_time - initial_time)
			best_eval.append(len(results[0]))
			print("ROUND #" + str(r+1) + " DONE!")

		time_eval.sort()
		best_eval.sort()
		print("\n--")
		print("MEAN SIZE OF BEST SCHEDULES FOUND:", statistics.mean(best_eval))
		print("STDEV SIZE OF BEST SCHEDULES FOUND:", statistics.stdev(best_eval))
		print("BEST SIZE OF BEST SCHEDULES FOUND:", best_eval[0])
		print("WORST SIZE OF BEST SCHEDULES FOUND:", best_eval[-1])
		print("--")
		print("MEAN EXECUTION TIME:", statistics.mean(time_eval))
		print("STDEV EXECUTION TIME:", statistics.stdev(time_eval))
		print("BEST EXECUTION TIME:", time_eval[0])
		print("WORST EXECUTION TIME:", time_eval[-1])
		print("--\n")
		print("==================================================\n")

#########################################################################################################################################
#########################################################################################################################################
#########################################################################################################################################

STOCHASTIC_K = 5
MAX_SLOT_SIZE = 800
FILE_PATH = "800-0.txt"

sinr = SINR(4, 20, 50, -90, MAX_SLOT_SIZE)
sinr.prepare(FILE_PATH)
scheduler = stochasticKGreedyScheduler(MAX_SLOT_SIZE, STOCHASTIC_K, sinr)

#scheduler.simpleExecution("s")
scheduler.experimentExecution(30, "s", seconds=20)