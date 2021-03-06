# -*- coding: utf8 -*-
import cv2
from scipy.spatial import distance
from imutils import face_utils
import imutils
import dlib
import numpy as np
import speech_recognition as sr
from threading import Thread
import serial
import struct
import time
class ee():
	def __init__(self):
		self.cap = cv2.VideoCapture(1)
		self.predict = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
		self.food = 0
		self.flag = 0
		self.thresh = 0.23 # nguong mo mat/mom
		self.frame_check = 30
		self.detect = dlib.get_frontal_face_detector() # nhan dien khuon mat su dung dlib
		self.mStart = face_utils.FACIAL_LANDMARKS_68_IDXS["mouth"][0]# lay cac diem cua mom tren khuon mat
		self.mEnd = face_utils.FACIAL_LANDMARKS_68_IDXS["mouth"][1]  
		self.eStart = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"][0] # lay diem cua mat
		self.eEnd = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"][1]
		self.flag_chose = 0 # kiem tra xem mat nhin ve huong do theo bao nhieu lau
		self.text_out = '' # render huong mat nhin
		self.side = 0 # kiem tra xem lan cuoi cung mat nhin di dau
		self.get_eye = True
		self.get_mouth = True
		self.x_eye = None
		self.mouth_cord = None
		self.kernel = np.ones((3,3), np.uint8)
		self.kernel1 = np.ones((5,5), np.uint8)
		#self.food_index = None #1: com, 2: thit, 3: rau
		self.sence = 1 # Giao dien 0 la menu, giao dien 1 la dk giong noi, giao dien 2 la dk = mat, giao dien 3 la thong tin nguoi dung va luong thuc an, calo
		self.food = 0
		self.change = False
		self.loading = True
		self.calib_done = False
		self.getLR = []
		self.x_left = 0
		self.x_right = 0
		self.time = 0
		self.x = 50
		self.y = 0
		self.check = 0
		self.ard = serial.Serial('/dev/ttyUSB0', 9600)
		self.w = True 
	def original_bgr(self):
		ret, frame = self.cap.read()
		return frame
	def get_contours(self, gray):
		_, thresh = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)
		ero = cv2.erode(thresh, self.kernel, iterations=1)
		cls = cv2.morphologyEx(ero, cv2.MORPH_CLOSE, self.kernel1)
		contours = cv2.findContours(cls, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
		return contours, cls
	def adjust_gamma(self, im):
		invGamma = 1.0 / 1.2
		table = np.array([((i / 255.0) ** invGamma) * 255
			for i in np.arange(0, 256)]).astype("uint8")
		return cv2.LUT(im, table)
	def get_x_left_right(self, frame):				
		cv2.putText(frame, 'Nhin con nguoi toi da', (5, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 3)
		if len(self.getLR) < 60:						
			self.getLR.append(self.x_eye)
		else:				
			self.x_left = min(self.getLR)
			self.x_right = max(self.getLR)		
			if self.x_left <= 16 and self.x_right >= 22:
				cv2.putText(frame, 'OK ', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 3)
				self.calib_done = True
				self.getLR = []
				print self.x_right, self.x_left
			else:
				cv2.putText(frame, 'Chua duoc', (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 3)
	def face_processing(self):	
		frame = self.original_bgr()
		frame = imutils.resize(frame, width=450)
		frame = self.adjust_gamma(frame)
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		subjects = self.detect(gray, 0)
		for subject in subjects:
			shape = self.predict(gray, subject)
			shape = face_utils.shape_to_np(shape)
			eye = shape[self.eStart:self.eEnd]
			if self.get_mouth == True:
				mouth = shape[self.mStart:self.mEnd]					
				self.mouth_cord = (mouth[3][0],int((mouth[9][1]+mouth[3][1])/2))
				#cv2.circle(frame, (mouth[3][0], 170), 4, (0,0,255), -1)
				cv2.circle(frame, (225, 170), 4, (0,0,255), -1)
				cv2.circle(frame, self.mouth_cord, 3, (0,255,255), -1)
				if self.mouth_cord[0] > 280 and self.x < 130:
					self.x+=1
					self.y = 0
				elif self.mouth_cord[0] < 120 and self.x > 0:
					self.x-=1
					self.y = 0
				if 120 < self.mouth_cord[0] < 280:
					self.x+=0
				#if self.mouth_cord[1] < 200 and self.y > 20:
					#self.y-=1
				#elif self.mouth_cord[1] > 130 and self.y < 80:
					#self.y+=1
				#if 130 < self.mouth_cord[1] < 200 :
					#self.y+=0
				mEar = distance.euclidean(mouth[3], mouth[9])
				print(mEar)
				if mEar > 60:
					self.time+=1
				if self.time > 6:
					self.y = 1
					self.time = 0
					print 'OK'
				else:
					self.y = 0
				if self.get_eye == False:
					eEar = self.get_aspect_ratio(eye)
					leftEyeHull = cv2.convexHull(eye)
					cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
					if eEar < self.thresh:
						self.flag += 1
						if self.flag > self.frame_check:
							self.get_eye = True
					else:
						self.flag = 0
				elif self.get_eye == True:
					cv2.circle(frame, (eye[0][0], eye[0][1]), 1, (0,0,255), -1)
					cv2.circle(frame, (eye[3][0], eye[3][1]), 1, (0,0,255), -1)
					roi = frame[eye[2][1]-5:eye[4][1]+5, eye[0][0]-5:eye[3][0]+5]
					roig = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
					contours, im = self.get_contours(roig)
					lengtc = len(contours)
					if lengtc > 0:
						area = [0.0]*lengtc
						for i in range(lengtc):
							area[i] = cv2.contourArea(contours[i])
						target_image = contours[area.index(max(area))]
						cord = cv2.moments(target_image)
						if cord['m00'] != 0:
							self.x_eye = int(cord['m10']/cord['m00'])
							y = int(cord['m01']/cord['m00'])
							cv2.circle(roi, (self.x_eye, y), 2, (255, 0, 0), -1)
							if self.calib_done == False:
								self.get_x_left_right(frame)
							else:
								if self.x_eye >= self.x_right-2:
									self.flag_chose += 1
									self.side = 1
								elif self.x_eye <= self.x_left+2:
									self.flag_chose += 1
									self.side = -1
								else:
									self.flag_chose = 0
									self.side = 0
									self.change = True
								#biggerEye = cv2.resize(roi, (60, 40))
								if self.flag_chose == 8 and self.side == -1:
									self.text_out = 'PHAI'
									if self.change == True:						
										self.food += 1 
										if self.food > 2:
											self.food = 2
										self.change = False
								if self.flag_chose == 8 and self.side == 1:
									self.text_out = 'TRAI'
									if self.change == True:
										self.food -= 1
										if self.food < 0:
											self.food = 0
										self.change = False
								cv2.putText(frame, self.text_out, (195, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 3)	
		self.ard.write(struct.pack('>BBB',self.y, v, self.x))
		return frame
	def get_aspect_ratio(self, obj):
		A = distance.euclidean(obj[1], obj[5])
		B = distance.euclidean(obj[2], obj[4])
		C = distance.euclidean(obj[0], obj[3])
		ear = (A + B)/(2 * C)
		return ear
	def control_arduino(self, port):
		ard = serial.Serial(port,9600)
		data = str(self.food_index)
		#while True:
			#ard.write(struct.pack('>BB',)
	def button(self, img, x, y, w, h, text):
		cv2.rectangle(img, (x,y), (w, h), (100,90,100), -1)
		cv2.putText(img, text, (20, 13), cv2.FONT_HERSHEY_COMPLEX, 0.5, (100,170,250), 2)
		return img
	def mouse(self, event, x, y, flags, param):
		if self.sence == 1:			
			if 160 <= x <= 448 and 90 <= y <= 150:
				if event == cv2.EVENT_LBUTTONDOWN:
					self.sence = 5
			elif 160 <= x <= 448 and 171 <= y <= 232:
				if event == cv2.EVENT_LBUTTONDOWN:
					self.sence = 5
			elif 160 <= x <= 448 and 330 <= y <= 390:
				if event == cv2.EVENT_LBUTTONDOWN:
					self.cap.release()					
					cv2.destroyAllWindows()					
					exit()
			elif 160 <= x < 448 and 250 <= y <= 312:
				if event == cv2.EVENT_LBUTTONDOWN:			
					self.sence = 2
		elif self.sence == 2:
			if 0 <= x <= 80 and 0 <= y <= 20:
				if event == cv2.EVENT_LBUTTONDOWN:
					self.sence = 1
		elif self.sence == 5:
			if 0 <= x <= 80 and 0 <= y <= 20:
				if event == cv2.EVENT_LBUTTONDOWN:
					self.sence = 1
	def display(self, food):
		global v
		v = 0
		cv2.namedWindow('GUI')
		cv2.setMouseCallback('GUI', self.mouse)
		sence_menu1 = cv2.imread('menu.jpg')
		sence_user2 = cv2.imread('user.jpg')
		while True:
			if self.loading == False:				
				if self.sence == 0:
					cv2.imshow('GUI', self.original_bgr())
				elif self.sence == 5:
					im = self.face_processing()
					bt = self.button(im, 0, 0, 80, 20, 'EXIT')
					cv2.imshow('GUI', bt)
					cv2.putText(food[self.food], self.text_out, (195, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 3)
					cv2.imshow('GUI1', food[self.food])
				elif self.sence == 1:
					cv2.imshow('GUI', sence_menu1)
				elif self.sence == 2:
					bt = self.button(sence_user2, 0, 0, 80, 20, 'EXIT')	
					cv2.imshow('GUI', bt)
				elif self.sence == 3:
					cv2.imshow('GUI', sence_voice3)
				elif self.sence == 4:
					cv2.imshow('GUI', sence_eye4)
			else:
				cv2.imshow('GUI', sence_menu1)
				self.loading = False
			cv2.waitKey(1)
def voice():
	global v
	while True:
		r = sr.Recognizer()
		with sr.Microphone() as source:
			print("Listen...")
			r.pause_threshold = 0.5
			r.threshold_energy = 1500
			r.adjust_for_ambient_noise(source, duration=0.5)
			audio = r.listen(source)
		try:
			comand = r.recognize_google(audio, language='vi-VN')
			if u'cơm' in comand:
				v = 0
			elif u'rau' in comand:
				v = 1
			elif u'thịt' in comand:
				v = 2			
			print("Ban noi:" + comand)
		except	sr.UnknownValueError:
			pass
food_img = [cv2.imread('food0.jpg'), cv2.imread('food1.jpg'), cv2.imread('food2.jpg')]
a = ee()
if __name__ == "__main__":
	t1 = Thread(target = a.display, args=(food_img,))
	t2 = Thread(target = voice)
	t1.setDaemon(True)
	t2.setDaemon(True)
	t1.start()
	t2.start()
	while True:
		pass 
