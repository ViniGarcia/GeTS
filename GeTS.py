############################################# GENETIC-BASED TRANSMISSION SCHEDULER - GeTS ###############################################

import sys
import copy
import math
import time
import numpy
import random
import statistics

#########################################################################################################################################
##################################################### GENETIC STRATEGY - RESOURCES ######################################################
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

class schedulerGenerator:

	__slot_maximum = None
	__sinr_manager = None

	def __init__(self, slot_maximum, sinr_manager):

		self.__slot_maximum = slot_maximum
		self.__sinr_manager = sinr_manager

		self.__device_list = self.__sinr_manager.devices()


	def __generateSlot(self, device_sublist):

		if self.__slot_maximum < len(device_sublist):
			slot_devices = random.sample(device_sublist, self.__slot_maximum)
		else:
			slot_devices = copy.copy(device_sublist)
		slot_candidate = [slot_devices.pop(0)]

		while True:
			if len(slot_devices) > 0:
				slot_candidate.append(slot_devices.pop(0))
			else:
				for device in slot_candidate:
					device_sublist.remove(device)
				return slot_candidate

			if self.__sinr_manager.check(slot_candidate):
				continue
			else:
				slot_candidate.pop()
				for device in slot_candidate:
					device_sublist.remove(device)
				return slot_candidate


	def generate(self):

		device_sublist = copy.copy(self.__device_list)
		stdma_candidate = []
		while len(device_sublist) > 0:
			stdma_candidate.append(self.__generateSlot(device_sublist))

		return stdma_candidate

#--

class schedulerCrossover:

	__crossover_probability = None
	__slot_maximum = None
	__sinr_manager = None

	def __init__(self, crossover_probability, slot_maximum, sinr_manager):

		self.__crossover_probability = crossover_probability
		self.__slot_maximum = slot_maximum
		self.__sinr_manager = sinr_manager


	def __crossoverTechnique(self, candidate_first, candidate_second):

		new_candidate = []
		
		devices_list = self.__sinr_manager.devices()
		outer_range = len(devices_list) // 2
		outer_adjust = len(devices_list) % 2

		for candidate in [candidate_first, candidate_second]:	
			crossover_counter = 0
			slot_index = 0

			while crossover_counter < outer_range and slot_index < len(candidate):
				new_slot = []
				for device in candidate[slot_index]:
					if device in devices_list:
						new_slot.append(device)
						devices_list.remove(device)
				if len(new_slot) > 0:
					new_candidate.append(new_slot)
					crossover_counter += len(new_slot)
				slot_index += 1
			
			outer_range += outer_adjust

		return new_candidate


	def cross(self, parents):

		if random.uniform(0.0, 1.0) <= self.__crossover_probability:

			return [self.__crossoverTechnique(parents[0], parents[1]), self.__crossoverTechnique(parents[1], parents[0])]

		return parents

#--

class schedulerMutation:

	__mutation_probability = None
	__slot_maximum = None
	__sinr_manager = None

	def __init__(self, mutation_probability, slot_maximum, sinr_manager):
	
		self.__mutation_probability = mutation_probability
		self.__slot_maximum = slot_maximum
		self.__sinr_manager = sinr_manager


	def mutate(self, parent):

		if random.uniform(0.0, 1.0) <= self.__mutation_probability:
			
			child = copy.copy(parent)

			if len(child) == 1:
				return child

			for attempt in range(2):
				slot_indexes = random.sample(list(range(len(child))), 2)
				mutation_slot = copy.copy(child[slot_indexes[0]])
				adding_slot = copy.copy(child[slot_indexes[1]])

				slot_index = 0
				while len(mutation_slot) < self.__slot_maximum and len(adding_slot) > 0:
					mutation_slot.append(adding_slot.pop())

				if self.__sinr_manager.check(mutation_slot):
					slot_remove = child[slot_indexes[1]]
					child.pop(slot_indexes[0])
					child.remove(slot_remove)
					child.append(mutation_slot)
					if len(adding_slot) > 0:
						child.append(adding_slot)
					break

			return child

		return parent

#--

class schedulerTournament:

	__tournament_spots = None

	def __init__(self, tournament_spots):

		self.__tournament_spots = tournament_spots


	def select(self, parents):

		competitors = []
		for index in range(self.__tournament_spots):
			competitors.append(parents[random.randint(0, len(parents)-1)])

		champion = competitors[0]
		for index in range(1, len(competitors)):
			if len(champion) > len(competitors[index]):
				champion = competitors[index]

		return champion

#--

class schedulerEvolution:

	__generator = None
	__crossover = None
	__mutator = None
	__selector = None
	__sinr = None

	def __init__(self, generator, crossover, mutator, selector, sinr, population):

		self.__generator = generator
		self.__crossover = crossover
		self.__mutator = mutator
		self.__selector = selector
		self.__sinr = sinr

		self.__population = population
		self.__current_population = []


	def __evolveCore(self):

		elitism_factor = self.__population//10
		new_population = self.__current_population[:elitism_factor]
		iterate_population = self.__current_population[elitism_factor:]

		while len(iterate_population) > 0:

			if len(iterate_population) == 1:
				iterate_population[0] = self.__mutator.mutate(iterate_population[0])
				new_population.append(iterate_population[0])
				break

			individual_one = self.__selector.select(iterate_population)
			iterate_population.remove(individual_one)
			individual_two = self.__selector.select(iterate_population)
			iterate_population.remove(individual_two)

			children = self.__crossover.cross([individual_one, individual_two])

			for child in children:
				new_population.append(self.__mutator.mutate(child))

		self.__current_population = new_population
		self.__current_population.sort(key = len)


	def reset(self):

		self.__sinr.reset()
		self.__current_population = []

	def evolveGenerations(self, generations):

		for individual in range(self.__population):
			self.__current_population.append(self.__generator.generate())

		for generation in range(generations):
			self.__evolveCore()

		return(self.__current_population)


	def evolveSeconds(self, seconds):

		for individual in range(self.__population):
			self.__current_population.append(self.__generator.generate())

		initial_time = time.time()
		while True:
			self.__evolveCore()
			if time.time() - initial_time >= seconds:
				break

		return(self.__current_population)


	def evolveLength(self, length, giveup):

		for individual in range(self.__population):
			self.__current_population.append(self.__generator.generate())

		static_generations = 0
		last_population = []
		while static_generations < giveup:
			self.__evolveCore()
			if len(self.__current_population[0]) <= length:
				break
			if self.__current_population == last_population:
				static_generations += 1
			else:
				static_generations = 0
				last_population = self.__current_population

		return(self.__current_population)


	def simpleExecution(self, mode, generations=1000, seconds=5, length=15):

		initial_time = time.time()
		if mode == "g":
			results = evolutor.evolveGenerations(generations)
		elif mode == "s":
			results = evolutor.evolveSeconds(seconds)
		elif mode == "l":
			results = evolutor.evolveLength(length, 5)
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


	def experimentExecution(self, rounds, mode, generations=1000, seconds=5, length=15):

		if type(rounds) != int or rounds < 2:
			print("\nINAVLID NUMBER OF ROUNDS!")
			return

		time_eval = []
		best_eval = []
		print("\n================ EXPERIMENT BEGIN ================\n")
		for r in range(rounds):
			self.reset()
			print("STARTING ROUND #" + str(r+1) + "!")
			initial_time = time.time()
			if mode == "g":
				results = evolutor.evolveGenerations(generations)
			elif mode == "s":
				results = evolutor.evolveSeconds(seconds)
			elif mode == "l":
				results = evolutor.evolveLength(length, 5)
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

SIZE_POPULATION = 30
MAX_SLOT_SIZE = 800
FILE_PATH = "800-0.txt"

sinr = SINR(4, 20, 50, -90, MAX_SLOT_SIZE)
sinr.prepare(FILE_PATH)

generator = schedulerGenerator(MAX_SLOT_SIZE, sinr)
crossover = schedulerCrossover(0.7, MAX_SLOT_SIZE, sinr)
mutator = schedulerMutation(0.7, MAX_SLOT_SIZE, sinr)
selector = schedulerTournament(2)
evolutor = schedulerEvolution(generator, crossover, mutator, selector, sinr, SIZE_POPULATION)

#evolutor.simpleExecution("s")
evolutor.experimentExecution(30, "s", seconds=20)