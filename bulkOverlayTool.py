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
            print("\nInvalid entry, please enter 'Y' or 'N'!\n")
def camRespToRefs(cam_resp):
    cam_name = cam_resp['name']
    cam_uid = cam_resp['uid']
    cam_object_type = cam_resp['objectType']
    cam_vsom_uid = cam_resp['vsomUid']
    cam_oper_state = cam_resp['operState']
    cam_ref = {'camName':cam_name,'camUid':cam_uid,'objectType':cam_object_type,'refVsomUid':cam_vsom_uid,'operState':cam_oper_state}

    return cam_ref

def getCamByLocation(location_name):
    location_uid = []
    camera_refs = []
    cameras_remaining = True
    print("Grabbing UID's for location: {0}".format(location_name))
    location_filter = {'filter':{'byLocationType':'DEFAULT','byLocalNameContains':location_name}}
    print("Using this filter for location search: \n{0}".format(location_filter))
    location_req = s.post('https://{0}/ismserver/json/location/v3_1/getLocations'.format(vsom_ip), json=location_filter, verify=False)
    location_resp = json.loads(location_req.text)
    if location_resp['data']['totalRows'] == 0:
        print("Got no location UID's!")
        return "Failed"
    for item in location_resp['data']['items']:
        if item['uid'] != '40000000-0000-0000-0000-000000000005':
            print(item)
            location_uid.append(item['uid'])

    if len(location_uid) > 1:
        continue_multiple_locations = getYorN(" Got more than one location. Continue? ")
        if continue_multiple_locations == False:
            print("Stopping! Try another spelling, or apply overlays manually.")
            return False
        else:
            start = 0
            limit = 100
            while cameras_remaining == True:
                cam_filter = {'filter':{'byLocationUids':location_uid,'pageInfo':{'start':start,'limit':limit}}}
                print("\n\nPaging: {0}\n\n".format(cam_filter['filter']['pageInfo']))
                get_cameras = s.post('https://{0}/ismserver/json/camera/v3_1/getCameras'.format(vsom_ip), json=cam_filter, verify=False)
                cam_resp = json.loads(get_cameras.text)
                for item in cam_resp['data']['items']:
                    camera_refs.append(camRespToRefs(item))
                print(cam_resp['data']['nextPageExists'])

                if cam_resp['data']['nextPageExists'] == True:
                    print("Need to get some more cameras.")
                    start += 100
                    limit += 100
                    print("Still got cameras? {0}".format(cameras_remaining))
                    time.sleep(1)

                if cam_resp['data']['nextPageExists'] == False:
                    cameras_remaining == False
                    print("Should have all cameras now.")

                    return camera_refs

    if len(location_uid) == 1:
        start = 0
        limit = 100
        times_run = 0
        print("Just one location.")
        while cameras_remaining == True:
            times_run += 1
            print(times_run)
            cam_filter = {'filter':{'byLocationUids':location_uid,'pageInfo':{'start':start,'limit':limit}}}
            get_cameras = s.post('https://{0}/ismserver/json/camera/v3_1/getCameras'.format(vsom_ip), json=cam_filter, verify=False)
            cam_resp = json.loads(get_cameras.text)
            for item in cam_resp['data']['items']:
                camera_refs.append(camRespToRefs(item))
            print(cam_resp['data']['nextPageExists'])
            if cam_resp['data']['nextPageExists'] == True:
                start += 100
                limit += 100
                time.sleep(1)
            if cam_resp['data']['nextPageExists'] == False:
                cameras_remaining == False
                return camera_refs

def getCameraDetails(cUid,camName,objectType,vsomUid):
    getCamPayload = {"cameraRef":{"refUid":cUid,"refName":camName,"refObjectType":objectType,"refVsomUid":vsomUid}}
    getCameraReq = s.post('https://{0}/ismserver/json/camera/v3_1/getCamera'.format(vsom_ip), json=getCamPayload, verify=False)
    camResp = json.loads(getCameraReq.text)
    camDetail = camResp['data']
    return camDetail

def checkRunningJobs():   #My intent with this function - if there are more than 10 queued jobs, I need to wait for that number to come down before running my below loop farther.
    runningJobs = True
    while runningJobs == True:
        print("\n===========================================\n")
        print("Checking running jobs.")
        getJobs = s.post('https://{0}/ismserver/json/job/v3_1/getAllJobCounts'.format(vsom_ip), verify=False)
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
    updateOverlayReq = s.post('https://{0}/ismserver/json/camera/v3_1/updateCamera'.format(vsom_ip), json=setOverlayPayload, verify=False)
    updateResp = json.loads(updateOverlayReq.text)
    if updateResp['status']['errorType'] == "SUCCESS":
        result = "Successfully updated {0}".format(camDetail['name'])
        print("\n========================={0}========================\n".format(result))
    else:
        error =  "Something must have went wrong here."
        print(error)


def mainLoop():
    try:
        print("To quit, just use ctrl+c!")
        location = str(input("Enter exact location name: "))
        try:
            s.post('https://{0}/ismserver/json/authentication/login'.format(vsom_ip), json=loginPayload, verify=False)
        except requests.exceptions.RequestException:
            print("Failed to login, check your IP address.")
            sys.exit()
        camera_list = getCamByLocation(location)
        if camera_list == "Failed":
            print("Something broked-ed, we got no cameras!")
        else:
            for item in camera_list:
                runningJobs = True
                if item['operState'] != "ok":
                    print(item)
                    print("\n\n**********Camera {0} appears disabled. Or something.**************\n\n".format(item['camName']))
                else:
                    cam_detail = getCameraDetails(item['camUid'],item['camName'],item['objectType'],item['refVsomUid'])
                    set_overlay = setCameraOverlay(cam_detail)
                    checkRunningJobs()
                    time.sleep(1)
    except KeyboardInterrupt:
        print("  You pushed ctrl+c or some other madness! Bye!")
        sys.exit()

s = requests.Session()
print("Some setup tasks first!!")
vsom_ip = str(input("Please enter the VSOM IP Address: "))  #Didn't test, but want to make sure the IP entered is stored as a string, dont' want python to guess.
vsmUsername = input("Please enter username: ")
vsmPassword = input("Please enter the password: ")
loginPayload = {"username":vsmUsername,"password":vsmPassword}

while True:
    mainLoop()
