# encoding: utf-8
import sys
import os
import sh
import random
import scipy
import math
import click
import time

def getDistance(xa, ya, xb, yb):
	dist = math.sqrt((xa-xb) **2 + (ya-yb)**2)
	return dist

def getDistanceMatrix(positions):
	matrix =[]
	numCandidatos = len(positions)

	for k in range(numCandidatos):
		vetoresPosition = positions[k]
		matrixPositions = []

		nUsers = len(vetoresPosition)

		for i in range(nUsers):
			a = vetoresPosition[i]
			linha = []
			for j in range(nUsers):
				b = vetoresPosition[j]
				dist = getDistance(a[0], a[1], b[0], b[1])
				linha.append(dist)
			matrixPositions.append(linha)

		matrix.append(matrixPositions)
	return matrix

if __name__ == "__main__": 	# Script apaga o conteúdo de "/positions/" e gera novos arquivos com as coordenados de acordo com as variáveis a seguir

	#////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	numSimula = 1 	#Quantidade de simulações
	numHost = 10   	#Quantidade de dispositivos

	#Define o espaço no qual os dispositivos são distribuídos de maneira aleatória
	x_inf = 0
	x_sup = 400
	y_inf = 0
	y_sup = 400

	#////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


	try:
		sh.rm(sh.glob('positions/*'))		
	except:
		print("Não foi possível deletar arquivos do diretório")


	
	random.seed(time.time())

	for i in range(numSimula):
		vetor = []
		for j in range(numHost):
			x = int(random.uniform(x_inf, x_sup))
			y = int(random.uniform(y_inf, y_sup))
			vetor.append([x,y])


		fileName = "positions/" + str(numHost) +'-' +  str(i)+ ".txt"				
		file = open(fileName, 'w')

		for j in range(numHost):
			par = vetor[j]
						#print(str(par[0]) + " " + str(par[1]))
			file.write(str(par[0]) + " " + str(par[1]) + "\n")