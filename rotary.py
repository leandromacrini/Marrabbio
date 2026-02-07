#!/usr/bin/python3
import gpiozero		#gpio module
import math, sys, os, time
import subprocess
import socket

pin_rotaryenable =  5
pin_countrotary = 6
pin_hook = 21

rotaryenable = gpiozero.Button(pin_rotaryenable, pull_up=False)
countrotary = gpiozero.Button(pin_countrotary, pull_up=False)
hook = gpiozero.Button(pin_hook, pull_up=False)

baseDir = "/home/licia/Marrabbio/marrabbio"

songs=[]

class Dial():
	def __init__(self):
		print("Initializing...")
		self.pulses = 0
		self.number = ""
		self.counting = False
		self.calling = False
		self.player = None
		
	def readSongsList(self):
		print("Reading songs list...")
		with open("/home/licia/Marrabbio/songs.txt") as f:
			lines = f.readlines()
		

		for line in lines:
			print("Adding song: %s" % line.strip())
			parts = line.split()
			newSong = {"number":parts[0], "file": baseDir + "/songs/" + ' '.join(parts[1:]) + ".mp3"}
			songs.append(newSong)
		
		print()
		print("Total songs found: %s" % len(lines))
	
	def matchSongs(self, number):
		print("matchSongs %s" % number)
		
		found = False
		for song in songs:
			if song['number'] == number:
				print("Song %s found: %s" % (song['number'], song['file']))
				self.reset()
				self.player = subprocess.Popen(["mpg123", "-q", song['file']], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				found = True
				break
		
		if not found:
			self.player = subprocess.Popen(["mpg123", "-q", baseDir + "/eggs/Utaimashou.mp3"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	def startcalling(self):
		print("Start calling")
		self.reset()
		self.calling = True
		self.player = subprocess.Popen(["mpg123", "--loop", "20", "-q", "/home/licia/Marrabbio/dial.mp3"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	def stopcalling(self):
		print("Stop calling")
		self.calling = False
		self.reset()

	def startcounting(self):
		print ("Start counting")
		self.counting = self.calling

	def stopcounting(self):
		print("Stop counting")
		if self.calling:
			print ("Got %s pulses.." % self.pulses)
			short_num=None
			if self.pulses > 0:
				if math.floor(self.pulses / 2) == 10:
					self.number += "0"
					short_num = "0"
				else:
					short_num = str(math.floor(self.pulses/2))
					self.number += short_num
			print("Than %s is dialed!" % self.number)
			self.pulses = 0

			if(short_num is not None):
				if(self.player):
					self.player.kill()
				
				self.player = subprocess.Popen(["mpg123", "-q", "/home/licia/Marrabbio/marrabbio/%s.mp3" % short_num], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				time.sleep(0.25)

				if len(self.number) == 3:
					time.sleep(0.75)
					self.matchSongs(self.number)


		self.counting = False

	def addpulse(self):
		print("Add pulse")
		if self.counting:
			self.pulses += 1
			print("freal addpulse %s" % self.pulses)

	def getnumber(self):
		return self.number

	def counterreset(self):
		print("Reset counter")
		self.pulses = 0
		self.number = ""

	def reset(self):
		print("Reset all")
		self.counterreset()
		try:
			self.player.kill()
		except:
			pass


if __name__ == "__main__":
	dial = Dial()
	dial.readSongsList()
	countrotary.when_deactivated = dial.addpulse
	countrotary.when_activated = dial.addpulse
	rotaryenable.when_activated = dial.startcounting
	rotaryenable.when_deactivated = dial.stopcounting
	hook.when_activated = dial.startcalling
	hook.when_deactivated = dial.stopcalling
	while True:
		time.sleep(1)
