import json
import requests
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def getYorN(prompt):
    while True:
        try:
            return {"Y":True,"N":False}[input(prompt).lower()]
        except KeyError:
            print("Invalid input, please enter 'Y' or 'N'!")

def getCamByLocation(locationName):
    serverFilter = {"filter":{"byLocationType":"DEFAULT","byLocalNameContains":locationName}}
    locationReq = s.post('https://{0}/ismserver/json/location/v3_1/getLocations'.format(vsmIp), json=serverFilter, verify=False)
    locationResp = json.loads(locationReq.text)
    print("\n=======Printing cam by server function=========\n")
    print(json.dumps(locationResp, indent=1))
    for item in locationResp['data']['items']:
        locationUid = []
        locationUid.append(item['uid'])
    camFilter = {"filter":{"byLocationUids":locationUid,"pageInfo":{"start":0,"limit":100}}}
    getCameras = s.post('https://{0}/ismserver/json/camera/v3_1/getCameras'.format(vsmIp), json=camFilter, verify=False)
    cameraResp = json.loads(getCameras.text)
    return cameraResp

def getCameraDetails(cUid,camName,objectType,vsomUid):
    getCamPayload = {"cameraRef":{"refUid":cUid,"refName":camName,"refObjectType":objectType,"refVsomUid":vsomUid}}
    getCameraReq = s.post('https://{0}/ismserver/json/camera/v3_1/getCamera'.format(vsmIp), json=getCamPayload, verify=False)
    camResp = json.loads(getCameraReq.text)
    camDetail = camResp['data']
    return camDetail

def checkRunningJobs():   #My intent with this function - if there are more than 10 queued jobs, I need to wait for that number to come down before running my below loop farther.
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
    overlay = {"additionalCameraSettings":{"textOverlaySetting":{"overlayPlacement":"BOTTOM_OF_IMAGE","timeStampEnabled":True,"timeStampAlignment":"CENTER","textDisplayEnabled":True,"textAlignment":"CENTER","displayText":overlayText}}}

    camDetail.update(overlay)
    setOverlayPayload = {"Device":camDetail,"addtlCameraActions":[]}
    #print("Printing the overlay payload we're gonna send: {0}".format(setOverlayPayload))
    updateOverlayReq = s.post('https://{0}/ismserver/json/camera/v3_1/updateCamera'.format(vsmIp), json=setOverlayPayload, verify=False)
    updateResp = json.loads(updateOverlayReq.text)
    if updateResp['status']['errorType'] == "SUCCESS":
        result = "Successfully updated {0}".format(camDetail['name'])
        print("\n========================={0}========================\n".format(result))
    else:
        error =  "Something must have went wrong here."
        print(error)

def mainLoop():
    print("To quit, just use ctrl+c!")
    location = str(input("Enter exact location name: "))
    s.post('https://{0}/ismserver/json/authentication/login'.format(vsmIp), json=loginPayload, verify=False)
    cameraList = getCamByLocation(location)
    if cameraList['data']['totalRows'] == 0:
        print("Something is wrong, we got no cameras!")
    else:
        for item in cameraList['data']['items']:
            runningJobs = True
            if item['operState'] != "ok":
                camName = item['name']
                print("\n\n\n******************************Camera {0} appears disabled or in error, skipping it!********************".format(camName))
            else:
                cUid = item['uid']
                vsomUid = item['vsomUid']
                objectType = item['objectType']
                camName = item['name']
                camDetail = getCameraDetails(cUid, camName, objectType, vsomUid)
                setOverlay = setCameraOverlay(camDetail)
                #Now check running jobs.  I'm worried that VSOM really doesn't handle jobs well.  And I do not want to queue 500 of these jobs, as
                #any more than 5 running jobs puts VSOM in like a blocking state, all new jobs are queued.  Is a pain.
                checkRunningJobs()
                time.sleep(1)

run = True

s = requests.Session()
print("Some setup tasks first!!")
vsmIp = str(input("Please enter the VSOM IP Address: "))  #Didn't test, but want to make sure the IP entered is stored as a string, dont' want python to guess.
vsmUsername = input("Please enter username: ")
vsmPassword = input("Please enter the password: ")
loginPayload = {"username":vsmUsername,"password":vsmPassword}

while True:
    mainLoop()
