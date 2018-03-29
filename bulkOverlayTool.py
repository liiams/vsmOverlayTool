import json
import requests
import time


s = requests.Session()
print("Some setup tasks first!!")
vsmIp = str(input("Please enter the VSOM IP Address: "))  #Didn't test, but want to make sure the IP entered is stored as a string, dont' want python to guess.
vsmUsername = input("Please enter username: ")
vsmPassword = input("Please enter the password: ")
loginPayload = {"username":vsmUsername,"password":vsmPassword}


def getCamByServer(serverName):
    serverFilter = {"filter":{"byNameContains":serverName,"pageInfo":{"start":0,"limit":100}}}
    serverReq = s.post('https://{0}/ismserver/json/server/v3_1/getServers'.format(vsmIp), json=serverFilter, verify=False)
    serverResp = json.loads(serverReq.text)
    return serverResp

def getCameraDetails(cUid,camName,objectType,vsomUid):
    getCamPayload = {"cameraRef":{"refUid":cUid,"refName":camName,"refObjectType":objectType,"refVsomUid":vsomUid}}
    getCameraReq = s.post('https://{0}/ismserver/json/camera/v3_1/getCamera'.format(vsmIp), json=getCamPayload, verify=False)
    camResp = json.loads(getCameraReq.text)
    camDetail = camResp['data']
    return camDetail

def checkRunningJobs():   #My intent with this function - if there are more than 10 queued jobs, I need to wait for that number to come down before running my below loop farther.
    while runningJobs == True:
        print("\n===========================================\n")
        print("Checking running jobs.")
        getJobs = s.post('https://{0}/ismserver/json/job/v3_1/getAllJobCounts'.format(vsmIp), verify=False)
        jobsList = json.loads(getJobs.text)
        print("\nCurrent running jobs: {0}\nCurrent pending jobs: {1}".format(jobsList['data']['runningJobsCount'],jobsList['data']['pendingJobsCount']))
        if jobsList['data']['runningJobsCount'] >= 5:
            print("\nRunning jobs full, checking queue!")
            if jobsList['data']['pendingJobsCount'] >= 10:
                print("\n==========================\nToo many pending jobs, sleep 5 seconds and try again!!!\n====================")
                time.sleep(5)
            else:
                runningJobs == False
                return


def setCameraOverlay(camDetail):
    print(camDetail)
    overlayText = camDetail['name']
    overlay = {"additionalCameraSettings":{"textOverlaySetting":{"overlayPlacement":"BOTTOM_OF_IMAGE","timeStampEnabled":True,"timeStampAlignment":"CENTER","textDisplayEnabled":True,"textAlignment":"CENTER","displayText":overlayText}}}

    camDetail.update(overlay)
    setOverlayPayload = {"Device":camDetail,"addtlCameraActions":[]}
    print("Printing the overlay payload we're gonna send: {0}".format(setOverlayPayload))
    updateOverlayReq = s.post('https://{0}/ismserver/json/camera/v3_1/updateCamera'.format(vsmIp), json=setOverlayPayload, verify=False)
    updateResp = json.loads(updateOverlayReq.text)
    if updateResp['status']['errorType'] == "SUCCESS":
        result = "Successfully updated {0}".format(camDetail['name'])
        print("\n========================={0}========================\n".format(result))
    else:
        error =  "Something must have went wrong here."
        print(error)

print("This tool will apply text overlays in bulk.  To make the job managegeable, we go by Media Server.\n")
print("Since not all media servers are connected all the time, you will input the name of the media server you want to start with.")
print("Don't typo the name.  Error handling is nonexistant for the time being!!!")

serverNameInput = str(input("Enter server name: "))

print("\n\n")
print("Got your server name, now going to get list of cameras.")
s.post('https://{0}/ismserver/json/authentication/login'.format(vsmIp), json=loginPayload, verify=False)

serverList = getCamByServer(serverNameInput)

if serverList['data']['totalRows'] > 1:
    print("We got more than 1 response, and now I'm broken!")

print("\n\n\n\nNow we're gonna loop through each camera, and apply the camera name as the overlay.\n\n")

for item in serverList['data']['items']:
    #print("Cameras we pulled to attempt setting overlay on below!\n")
    #print(json.dumps(item['retentionInfos'], indent=1))
    for d in item['retentionInfos']:
        runningJobs = True
        cUid = d['cameraRef']['refUid']
        vsomUid = d['cameraRef']['refVsomUid']
        objectType = d['cameraRef']['refObjectType']
        camName = d['cameraRef']['refName']
        camDetail = getCameraDetails(cUid, camName, objectType, vsomUid)
        setOverlay = setCameraOverlay(camDetail)
        #Now check running jobs.  I'm worried that VSOM really doesn't handle jobs well.  And I do not want to queue 500 of these jobs, as
        #any more than 5 running jobs puts VSOM in like a blocking state, all new jobs are queued.  Is a pain.
        checkRunningJobs()
        time.sleep(2)

        #print(setOverlay)
