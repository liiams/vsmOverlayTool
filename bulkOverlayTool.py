import getpass
import json
import requests
import sys
import time


import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def getYorN(prompt):
    while True:
        try:
            return {"y":True,"n":False}[input(prompt).lower()]
        except KeyError:
            print("Invalid input, please enter 'Y' or 'N'!")

def getCamByLocation(locationName):
    start = 0
    more_pages = True
    locationUid = []
    cameras = []
    locationFilter = {"filter":{"byLocationType":"DEFAULT","byLocalNameContains":locationName}}
    locationReq = s.post('https://{0}/ismserver/json/location/v3_1/getLocations'.format(vsmIp), json=locationFilter, verify=False)
    locationResp = json.loads(locationReq.text)
    for item in locationResp['data']['items']:
        locationUid.append(item['uid'])

    if len(locationUid) > 1:
        keep_going = getYorN("Got more than one location. Continue?")
        if keep_going == False:
            print("Stopping!!!")
            return False
    while more_pages == True:
        camFilter = {"filter":{"byLocationUids":locationUid,"pageInfo":{"start":start,"limit":500}}}
        getCameras = s.post('https://{0}/ismserver/json/camera/v3_1/getCameras'.format(vsmIp), json=camFilter, verify=False)
        cameraResp = json.loads(getCameras.text)
        for item in cameraResp['data']['items']:
            cameras.append(item)
        if cameraResp['data']['nextPageExists'] == True:
            start += 500
            limit += 500
        elif cameraResp['data']['nextPageExists'] == False:
            more_pages = False

    return cameras

def getCameraDetails(cUid,camName,objectType,vsomUid):
    getCamPayload = {"cameraRef":{"refUid":cUid,"refName":camName,"refObjectType":objectType,"refVsomUid":vsomUid}}
    getCameraReq = s.post('https://{0}/ismserver/json/camera/v3_1/getCamera'.format(vsmIp), json=getCamPayload, verify=False)
    camResp = json.loads(getCameraReq.text)
    camDetail = camResp['data']
    return camDetail

def checkRunningJobs():   #My intent with this function - if there are more than 5 queued jobs, I need to wait for that number to come down before running my below loop farther.
    runningJobs = True
    while runningJobs == True:
        print("\n===========================================\n")
        print("Checking running jobs.")
        getJobs = s.post('https://{0}/ismserver/json/job/v3_1/getAllJobCounts'.format(vsmIp), verify=False)
        jobsList = json.loads(getJobs.text)
        print("\nCurrent running jobs: {0}\nCurrent pending jobs: {1}".format(jobsList['data']['runningJobsCount'],jobsList['data']['pendingJobsCount']))
        if jobsList['data']['runningJobsCount'] >= 5:
            print("\nRunning jobs full, checking queue!")
            time.sleep(5)
            if jobsList['data']['pendingJobsCount'] >= 10:
                print("\n==========================\nToo many pending jobs, sleep 5 seconds and try again!!!\n====================")
                time.sleep(5)
        else:
            runningJobs == False
            return


def setCameraOverlay(camDetail):
    #print(camDetail)  #Prints camera payload before adding overlay specific parameters!
    overlayText = camDetail['name']
    overlay = {"additionalCameraSettings":{"textOverlaySetting":{"overlayPlacement":overlay_top_bottom,"timeStampEnabled":True,"timeStampAlignment":time_stamp_alignment,"textDisplayEnabled":True,"textAlignment":text_alignment,"displayText":overlayText}}}
    print(overlay)
    camDetail.update(overlay)
    setOverlayPayload = {"Device":camDetail,"addtlCameraActions":[]}
    #print("Printing the overlay payload we're gonna send: {0}".format(setOverlayPayload))
    updateOverlayReq = s.post('https://{0}/ismserver/json/camera/v3_1/updateCamera'.format(vsmIp), json=setOverlayPayload, verify=False)
    updateResp = json.loads(updateOverlayReq.text)
    if updateResp['status']['errorType'] == "SUCCESS":
        result = "Successfully updated {0}".format(camDetail['name'])
        print("\n========================={0}========================\n".format(result))
        return True
    else:
        error =  "Something must have went wrong here."
        print(error)
        return False

def mainLoop():
    try:
        #initialize counters
        overlay_successful = 0
        overlay_fail = 0
        print("To quit, just use ctrl+c!")
        #prompt for location string
        location = input("Enter exact location name: ")
        #set up login payload for VSM.
        loginPayload = {"username":vsmUsername,"password":vsmPassword}
        #establish http session, login to VSM.
        s.post('https://{0}/ismserver/json/authentication/login'.format(vsmIp), json=loginPayload, verify=False)
        #Get our camera list - function defined above
        cameras = getCamByLocation(location)
        if cameras == False:
            print("Aborted!")
            return
        if len(cameras) == 0:
            print("Something is wrong, we got no cameras!")
        else:
            for item in cameras:
                runningJobs = True
                cUid = item['uid']
                vsomUid = item['vsomUid']
                objectType = item['objectType']
                camName = item['name']
                camDetail = getCameraDetails(cUid, camName, objectType, vsomUid)
                setOverlay = setCameraOverlay(camDetail)
                if setOverlay == True:
                    overlay_successful += 1
                elif setOverlay == False:
                    overlay_fail += 1
                    #Now check running jobs.  I'm worried that VSOM really doesn't handle jobs well.  And I do not want to queue 500 of these jobs, as
                    #any more than 5 running jobs puts VSOM in like a blocking state, all new jobs are queued.  Is a pain.
                checkRunningJobs()
                time.sleep(1)
        print("\n\n\nSuccessfully applied overlay to {0} devices, while {1} failed.  Scroll up for details.\n\n\n\n\n\n".format(overlay_successful,overlay_fail))
    except KeyboardInterrupt:
        print("Got SIGTERM, exiting the program!")
        sys.exit()

if __name__ == "__main__":
    #Set up requests session
    s = requests.Session()
    try:
        overlay_verical = False
        text_horizontal = False
        time_horizontal = False
        print("Some setup tasks first!!")
        vsmIp = input("Please enter the VSOM IP Address: ")
        vsmUsername = input("Please enter username: ")
        vsmPassword = getpass.getpass()
        while overlay_vertical == False:
            overlay_top_bottom = input("Will the text overlay be at the TOP or BOTTOM of the image? ").upper()
            if overlay_top_bottom != "TOP" or overlay_top_bottom != "BOTTOM":
                print("Invalid input, please try again.  Valid input is either 'TOP' or 'BOTTOM'.")
            else:
                overlay_vertical = True
        while text_horizontal == False:
            text_alignment = input("Horizontal alignment for text? 'LEFT', 'RIGHT', or 'CENTER': ").upper()
            if text_alignment != "LEFT" or text_alignment != "RIGHT" or text_alignment != "CENTER":
                print("Please enter a valid option. 'LEFT', 'RIGHT' or 'CENTER'.")
            else:
                text_horizontal = True
        while time_horizontal == False:
            time_stamp_alignment = input("You know the drill by now, timespamp alignment. LEFT, RIGHT, CENTER: ").upper()
            if time_stamp_alignment != "LEFT" or time_stamp_alignment != "RIGHT" or time_stamp_alignment != "CENTER":
                print("Really man? Get in the game! LEFT, RIGHT or CENTER!")
            else:
                time_horizontal = True
    except KeyboardInterrupt:
        print("Got SIGTERM, exiting the program!")
        sys.exit()

    while True:
        #infinitely loop our main function
        mainLoop()
