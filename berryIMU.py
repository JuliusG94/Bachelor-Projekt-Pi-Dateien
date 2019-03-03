#!/usr/bin/python
#
#	This program  reads the angles from the acceleromter, gyrscope
#	and mangnetometeron a BerryIMU connected to a Raspberry Pi.
#
#	Both the BerryIMUv1 and BerryIMUv2 are supported
#
#	BerryIMUv1 uses LSM9DS0 IMU
#	BerryIMUv2 uses LSM9DS1 IMU
#
#	This program includes a number of calculations to improve the
#	values returned from BerryIMU. If this is new to you, it
#	may be worthwhile first to look at berryIMU-simple.py, which
#	has a much more simplified version of code which would be easier
#	to read.
#
#	http://ozzmaker.com/

import time
import math
import IMU
import datetime
import threading
import globalKalman

IMU.detectIMU()  # Detect if BerryIMUv1 or BerryIMUv2 is connected.
IMU.initIMU()  # Initialise the accelerometer, gyroscope and compass

# If the IMU is upside down (Skull logo facing up), change this value to 1
IMU_UPSIDE_DOWN = 0

RAD_TO_DEG = 57.29578
M_PI = 3.14159265358979323846
G_GAIN = 0.070  # [deg/s/LSB]  If you change the dps for gyro, you need to update this value accordingly
AA = 0.40  # Complementary filter constant

################# Compass Calibration values ############
# Use calibrateBerryIMU.py to get calibration values
# Calibrating the compass isnt mandatory, however a calibrated
# compass will result in a more accurate heading value.

magXmin = 0
magYmin = 0
magZmin = 0
magXmax = 0
magYmax = 0
magZmax = 0

'''
Here is an example:
magXmin =  -1748
magYmin =  -1025
magZmin =  -1876
magXmax =  959
magYmax =  1651
magZmax =  708
Dont use the above values, these are just an example.
'''

##########################################################

# global variables for computed gyro angle values (degrees per second)
gyroXangle = 0.0
gyroYangle = 0.0
gyroZangle = 0.0
a = datetime.datetime.now()

class Sensor(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def readAndComputeSensorValues(self):

        while True:
            # Get lock to synchronize threads
            lock.acquire()

            # Read the accelerometer,gyroscope and magnetometer values
            ACCx = IMU.readACCx()
            ACCy = IMU.readACCy()
            ACCz = IMU.readACCz()
            GYRx = IMU.readGYRx()
            GYRy = IMU.readGYRy()
            GYRz = IMU.readGYRz()
            MAGx = IMU.readMAGx()
            MAGy = IMU.readMAGy()
            MAGz = IMU.readMAGz()

            ################## Further computation, compensation, filtering etc. ################

            # Apply compass calibration
            MAGx -= (magXmin + magXmax) / 2
            MAGy -= (magYmin + magYmax) / 2
            MAGz -= (magZmin + magZmax) / 2

            ##Calculate loop Period(LP). How long between Gyro Reads
            global a
            b = datetime.datetime.now() - a
            a = datetime.datetime.now()
            LP = b.microseconds / (1000000 * 1.0)
            #print("Loop Time %5.2f " % LP)

            # Convert Gyro raw to degrees per second
            rate_gyr_x = GYRx * G_GAIN
            rate_gyr_y = GYRy * G_GAIN
            rate_gyr_z = GYRz * G_GAIN

            # Calculate the angles from the gyro.
            global gyroXangle
            global gyroYangle
            global gyroZangle
            gyroXangle += rate_gyr_x * LP
            gyroYangle += rate_gyr_y * LP
            gyroZangle += rate_gyr_z * LP

            # Convert Accelerometer values to degrees
            if not IMU_UPSIDE_DOWN:
                # If the IMU is up the correct way (Skull logo facing down), use these calculations
                AccXangle = (math.atan2(ACCy, ACCz) * RAD_TO_DEG)
                AccYangle = (math.atan2(ACCz, ACCx) + M_PI) * RAD_TO_DEG
            else:
                # Us these four lines when the IMU is upside down. Skull logo is facing up
                AccXangle = (math.atan2(-ACCy, -ACCz) * RAD_TO_DEG)
                AccYangle = (math.atan2(-ACCz, -ACCx) + M_PI) * RAD_TO_DEG

            # Change the rotation value of the accelerometer to -/+ 180 and
            # move the Y axis '0' point to up.  This makes it easier to read.
            if AccYangle > 90:
                AccYangle -= 270.0
            else:
                AccYangle += 90.0

            # If IMU is upside down, this is needed to get correct heading.
            if IMU_UPSIDE_DOWN:
                MAGy = -MAGy

            # Calculate heading
            heading = 180 * math.atan2(MAGy, MAGx) / M_PI

            # Only have our heading between 0 and 360
            if heading < 0:
                heading += 360

            ####################################################################
            ###################Tilt compensated heading#########################
            ####################################################################
            # Normalize accelerometer raw values.
            if not IMU_UPSIDE_DOWN:
                # Use these two lines when the IMU is up the right way. Skull logo is facing down
                accXnorm = ACCx / math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)
                accYnorm = ACCy / math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)
            else:
                # Us these four lines when the IMU is upside down. Skull logo is facing up
                accXnorm = -ACCx / math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)
                accYnorm = ACCy / math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)

            # Calculate pitch and roll
            pitch = math.asin(accXnorm)
            roll = -math.asin(accYnorm / math.cos(pitch))

            # Calculate the new tilt compensated values
            magXcomp = MAGx * math.cos(pitch) + MAGz * math.sin(pitch)

            # The compass and accelerometer are orientated differently on the LSM9DS0 and LSM9DS1 and the Z axis on the compass

            magYcomp = MAGx * math.sin(roll) * math.sin(pitch) + MAGy * math.cos(roll) + MAGz * math.sin(roll) * math.cos(
                pitch)  # LSM9DS1

            # Calculate tilt compensated heading
            tiltCompensatedHeading = 180 * math.atan2(magYcomp, magXcomp) / M_PI

            if tiltCompensatedHeading < 0:
                tiltCompensatedHeading += 360

            ############################ END ##################################

            if 0:  # Change to '0' to stop showing the angles from the accelerometer
                print("# ACCX Angle %5.2f ACCY Angle %5.2f #  " % (AccXangle, AccYangle)),

            if 0:  # Change to '0' to stop  showing the angles from the gyro
                print("\t# GRYX Angle %5.2f  GYRY Angle %5.2f  GYRZ Angle %5.2f # " % (gyroXangle, gyroYangle, gyroZangle)),

            if 0:  # Change to '0' to stop  showing the heading
                print("\t# HEADING %5.2f  tiltCompensatedHeading %5.2f #" % (heading, tiltCompensatedHeading)),

            # print a new line
            #print("")

            # slow program down a bit, makes the output more readable
            time.sleep(0.03)

            # Free lock to release next thread
            lock.release()

    def run(self):
        self.readAndComputeSensorValues()

lock = threading.Lock()