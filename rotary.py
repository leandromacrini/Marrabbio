#!/usr/bin/python3
import gpiozero		#gpio module
import time
import threading
import subprocess
from gpiozero import Device

pin_rotaryenable =  5
pin_countrotary = 6
pin_hook = 21

rotaryenable = gpiozero.Button(pin_rotaryenable, pull_up=False, bounce_time=0.01)
countrotary = gpiozero.Button(pin_countrotary, pull_up=False, bounce_time=0.004)
hook = gpiozero.Button(pin_hook, pull_up=False, bounce_time=0.02)

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
		self.lock = threading.Lock()
		
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
				self.player = subprocess.Popen(["mpg123", "-q", song['file']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
				found = True
				break
		
		if not found:
			self.player = subprocess.Popen(["mpg123", "-q", baseDir + "/eggs/Utaimashou.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

	def startcalling(self):
		print("Start calling")
		self.reset()
		self.calling = True
		self.player = subprocess.Popen(["mpg123", "--loop", "20", "-q", "/home/licia/Marrabbio/dial.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

	def stopcalling(self):
		print("Stop calling")
		self.calling = False
		self.reset()

	def startcounting(self):
		print ("Start counting")
		with self.lock:
			self.counting = self.calling
			self.pulses = 0

	def stopcounting(self):
		print("Stop counting")
		with self.lock:
			calling = self.calling
			pulses = self.pulses
			self.pulses = 0
			self.counting = False

		if not calling:
			return

		print("Got %s pulses.." % pulses)
		short_num = None
		if pulses == 10:
			short_num = "0"
		elif 1 <= pulses <= 9:
			short_num = str(pulses)
		elif pulses > 0:
			print("Unexpected pulses count: %s" % pulses)

		if short_num is None:
			return

		self.number += short_num
		print("Than %s is dialed!" % self.number)

		if self.player:
			self.player.kill()

		self.player = subprocess.Popen(["mpg123", "-q", "/home/licia/Marrabbio/marrabbio/%s.mp3" % short_num], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

		if len(self.number) == 3:
			number = self.number
			threading.Timer(0.75, self.matchSongs, args=(number,)).start()

	def addpulse(self):
		with self.lock:
			if self.counting:
				self.pulses += 1
				print("Pulse %s" % self.pulses)

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
	print("gpiozero pin factory: %s" % Device.pin_factory)
	dial = Dial()
	dial.readSongsList()
	countrotary.when_activated = dial.addpulse
	rotaryenable.when_activated = dial.startcounting
	rotaryenable.when_deactivated = dial.stopcounting
	hook.when_activated = dial.startcalling
	hook.when_deactivated = dial.stopcalling
	while True:
		time.sleep(1)
