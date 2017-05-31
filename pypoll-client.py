#!/usr/bin/env python
from __future__ import print_function
import socket
from threading import Thread
import Queue
#import time
import ssl
import argparse

globalWorkDone = False

def eprint(*args, **kwargs):
	import sys
	print(*args, file=sys.stderr, **kwargs)

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
	def isDone(self):
		return self.done
	def run(self):
		with open(self.fileName, 'r') as f:
			for line in f:				# While we're here, we should probably take some time to sanitize our input.
				if line.rstrip() == '':	# if empty line, skip it
					continue
				self.fileQueue.put(line.rstrip())
				self.i = self.i + 1
		self.done = True
		self.fileQueue.put(None)		# This is a signal that we've read all data.

# fileWriter is a bit harder - we must explicity tell it when its done.
# As long as we do not call procDone(), the fileWriter object will continue to poll the queue
# for strings, and write them to the specified file. Calls can block, so program
# never terminates. Call procDone() before writing the last string.
class fileWriter(Thread):
	def __init__(self, fileName, fileQueue):
		Thread.__init__(self)
		self.fileName = fileName
		self.done = False
		self.fileQueue = fileQueue
		self.i = 0
	def procDone(self):
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

# Meat and potatoes goes here. This thread consumes data from the
# input queue, uses it to reach out to servers, get their json, 
# and send it to the output queue.
class serverPoller(Thread):
	def __init__(self, name, inputQueue, outputQueue):
		Thread.__init__(self)
		self.inQueue = inputQueue
		self.outQueue = outputQueue
		self.done = False
		self.name = name
	def run(self):
		global globalWorkDone
		while not globalWorkDone:
			host = self.inQueue.get()
			if host == None:			# We got the last entry.
				globalWorkDone = True
				break
			port = 25560
			s = socket.socket()
			s.settimeout(10)			# Try for 10 sec
			try:
				s.connect((host, port))
				gotString = s.recv(8192)
				self.outQueue.put(gotString)
			except socket.timeout as e:
				eprint("Failed to connect to {} - the connection timed out.".format(host))
			finally:
				self.inQueue.task_done()
				s.close()

def main():
	desc = "PyPoll is a suite of two programs, a client and a server. The server runs as a daemon on any machines desired. When a client connects to a server, the server responds by generating JSON-formatted information about itself, including cpu utilization, disk free space, and more. The client (this program) may be configured to output this JSON to a file or to stdio."
	ep   = "The addresses in inputFile may be hostnames or IPv4 addresses. There must be one address per line. PyPoll doesn't do much sanity checking on this file, so strange things may happen if it is formatted incorrectly. Hostname resolution is handled by the underlying system."
	parser = argparse.ArgumentParser(description=desc, epilog=ep)
	parser.add_argument('-i', '--inputFile', help='Location of the file that stores the addresses to poll.', required=True)
	parser.add_argument('-o', '--outputFile', help='Location of the file that will store the polled info. Overwrites existing file. Stdout if none.')
	parser.add_argument('-t', '--threads', help='Number of threads to run. Default is 1.', type=int, default=1)
	args = parser.parse_args()
	addrQueue = Queue.Queue()
	resultQueue = Queue.Queue()
	myReader = fileReader(args.inputFile, addrQueue)
	myWriter = fileWriter(args.outputFile, resultQueue)
	myReader.start()
	myWriter.start()
	threads = []
	for i in xrange(args.threads):
		threads.append(serverPoller(i, addrQueue, resultQueue))
		threads[i].start()
	myReader.join()
	for worker in threads:
		worker.join()
	myWriter.procDone()
	resultQueue.put("jobdone")


if __name__ == "__main__":
	main()
