import os
import time
import subprocess
from subprocess import Popen, PIPE

passwordFile = "/root/containerPassword.txt"
containerFile = "/mnt/sda1/container.bin"

NO_USB_DRIVE = 1
USB_DRIVE_MOUNTED = 2
NO_CONTAINER = 3
CONTAINER_MOUNTED = 4
CONTAINER_ERROR = 5
NO_CONTAINER_PASSWORD = 6

def driveIsMounted():
    mountCheckResult = ''

    mountCheckResult = subprocess.run(['mount'], stdout=subprocess.PIPE, universal_newlines=True)

    if "container" in mountCheckResult.stdout:
        return True
    
    return False

def afterMountedSetup():
    if not os.path.isdir('/root/encrypted_container'):
        process = subprocess.run("ln -s /tmp/container/ /root/encrypted_container", shell=True)
    process = subprocess.run("dropbear -P /var/run/dropbear2.pid -p 2222 -K 300 -T 3", shell=True)

def checkDriveState(driveStateParam):

    if not os.path.isfile(passwordFile):
        return NO_CONTAINER_PASSWORD

    # check if the drive is already mounted:
    if driveStateParam != CONTAINER_MOUNTED and driveIsMounted():
        driveStateParam = CONTAINER_MOUNTED
        afterMountedSetup()
        return driveStateParam
        

    sdaCheckResult = ''

    sdaCheckResult = subprocess.run(['ls', '/dev'], stdout=subprocess.PIPE, universal_newlines=True)

    if not "sda1" in sdaCheckResult.stdout:
        if driveStateParam != NO_USB_DRIVE:
            # got unplugged...
            # just do a reboot for now?
            # needed because dev mapper will allow it to continue to be written too even
            # though the disk is gone
            subprocess.run(['reboot'])
        return NO_USB_DRIVE
    elif driveStateParam == NO_USB_DRIVE:
        driveStateParam = USB_DRIVE_MOUNTED

    if driveStateParam == USB_DRIVE_MOUNTED and not os.path.isfile(containerFile):
        return NO_CONTAINER

    if driveStateParam == USB_DRIVE_MOUNTED or driveStateParam == NO_CONTAINER and os.path.isfile(containerFile):
        #get the password
        containerPassword = ""
        with open(passwordFile) as passwordFileHandle:
            containerPassword = passwordFileHandle.readline().rstrip()

        #attempt to mount the container
        process = subprocess.run("mkdir /tmp/container", shell=True)

        process = Popen(["cryptsetup", "luksOpen", containerFile, "container"], stdin=PIPE)
        process.communicate((containerPassword + "\n").encode("ascii"))
        process.wait()

        time.sleep(5)

        process = subprocess.run("mount /dev/mapper/container /tmp/container/ && sleep 5", shell=True)

        #actually check if the conatiner mounted

        if driveIsMounted():
            afterMountedSetup()
            driveStateParam = CONTAINER_MOUNTED

        else:
            driveStateParam = CONTAINER_ERROR

    return driveStateParam


def main():
    currentDriveState = NO_USB_DRIVE

    while True:

        currentDriveState = checkDriveState(currentDriveState)

        driveStatePath = '/tmp/driveState.txt'
        driveStateFile = open(driveStatePath, 'w')

        driveStateFile.write(currentDriveState.name)

        time.sleep(1)


if __name__ == "__main__":
    main()
