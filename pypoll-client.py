#!/usr/bin/env python

import socket
from threading import Thread
import Queue
#import time
import ssl
import argparse

# This thread will read data from our input file to the data in queue.
# Since the file is a finite length, we actually know for sure when this
# thread finishes. It can report as much to the outside world
class fileReader(Thread):
	def __init__(self, fileName, fileQueue):
		Thread.__init__(self)
		self.fileName = fileName
		self.done = False
		self.fileQueue = fileQueue
		self.i = 0
	def isDone():
		return self.done
	def run(self):
		with open(self.fileName, 'r') as f:
			for line in f:
				self.fileQueue.put(line.rstrip())
				self.i = self.i + 1
		self.done = True
		print("fileReader done, added {} lines.".format(self.i)

# fileWriter is a bit harder - we must explicity tell it when its done.
# As long as we do not call procDone(), the fileWriter object will continue to poll the queue
# for strings, and write them to the specified file. Call procDone() before writing the last
# string.
class fileWriter(Thread):
	def __init__(self, fileName, fileQueue):
		Thread.__init__(self)
		self.fileName = fileName
		self.done = False
		self.fileQueue = fileQueue
		self.i = 0
	def procDone():
		self.done = True
	def run(self):
		if not self.fileName == None:
			with open(self.fileName, 'w') as f:
				while not self.done:
					line = self.fileQueue.get()
					if line == "jobdone": break
					f.write("{}\n".format(line))
					self.fileQueue.task_done()
		else:
			while not self.done:
				line = self.fileQueue.get()
				if line == "jobdone": break
				print(line)
				self.fileQueue.task_done()

class serverPoller(Thread):
	def __init__(self, inputQueue, outputQueue):
		Thread.__init__(self)
		self.inQueue = inputQueue
		self.outQueue = outputQueue
		self.done = False
	def run():
		while true:
			host = self.inQueue.get()
			port = 25560
			s = socket.socket()
			s.connect((host, port))
			outputQueue.put(s.recv(4096))
			self.inQueue.task_done()

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-i', '--inputFile', help='Location of the file that stores the addresses to poll', required=True)
	parser.add_argument('-o', '--outputFile', help='Location of the file that will store the polled info. Stdout if none.')
	parser.add_argument('-t', '--threads', help='Number of threads to run', type=int, default=1)
	args = parser.parse_args()
	addrQueue = Queue()
	resultQueue = Queue()
	myReader = fileReader(args.inputFile, addrQueue)
	myWriter = fileWriter(args.outputFile, resultQueue)
	myReader.start()
	print("reader start")
	myWriter.start()
	print("writer start")
	threads = []
	for i in xrange(args.threads):
		threads.append(serverPoller(addrQueue, resultQueue))
		threads[i].start()
		print("worker {} start".format(i))
	myReader.join()
	print("reader join()")
	for worker in threads:
		worker.join()
		print("another worker join")
	myWriter.procDone()
	resultQueue.put("jobdone")


if __name__ == "__main__":
	main()

