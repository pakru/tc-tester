#!/usr/local/bin/python3.5

import paramiko
import time
import sys
import os
import subprocess
import hc_module.ecss_config_http_commands as HT
import colorama
from colorama import Fore, Back, Style
import xml.etree.ElementTree as ET
import requests
import signal
import pjSIP_py.pjUA as pjua
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import ssh_cocon.ssh_cocon as ccn

login = str(os.environ.get('COCON_USER'))
password = str(os.environ.get('COCON_PASS'))

host = str(os.environ.get('SSW_IP'))
port = int(os.environ.get('COCON_PORT'))

testingDomain = str(os.environ.get('TC_TEST_DOMAIN_NAME'))
testingDomainSIPport = str( int(os.environ.get('SSW_PORT'))+2 )
testingDomainSIPaddr = str(os.environ.get('SSW_IP'))
coreNode='core1@ecss1'
sipNode='sip1@ecss1'
dsNode='ds1@ecss1'
sippPath = str(os.environ.get('SIPP_PATH'))
sippListenAddress=str(os.environ.get('TC_EXT_TRUNK_IP'))
sippListenPort='15076'
sippMediaListenPort='16016'
sippMediaListenPortTrunk='17016'

masterNumber = str(os.environ.get('TC_MASTER_NUMBER'))
secondaryMaster = str(int(masterNumber) + 1)
masterSIPpass = str(os.environ.get('TC_MASTER_NUMBER'))
SIPgroup = str(os.environ.get('SIP_GROUP'))
restHost = str(os.environ.get('TC_REST_HOST'))
restPort = str(os.environ.get('TC_REST_PORT'))
testTemplateName=str(os.environ.get('TC_TEMPLATE_NAME'))

tcPath = str(os.environ.get('TC_PATH'))
tcRoutingName='test_tc'
tcExtTrunkName='toSIPp'
tcExtTrunkIP=str(os.environ.get('TC_EXT_TRUNK_IP'))
tcExtTrunkPort=str(os.environ.get('TC_EXT_TRUNK_PORT'))
tcClientCount=str(os.environ.get('TC_CLIENT_COUNT'))
tcClientNumberPrefix=str(os.environ.get('TC_CLIENT_NUMBER_PREFIX'))
tcMembers='20{01-20}'
tcExtMember = '2020'
tcUACCount = 5

recievedPOSTstr = ''

class YeaPhone():
	def __init__():
		pass
	def parseXML():
		pass

# HTTPRequestHandler class
class testHTTPServer_RequestHandler(BaseHTTPRequestHandler):
 
# GET
	def do_GET(self):
		# Send response status code
		self.send_response(200)
		print('Recieved POST message')
		print('Recieved data: ' + str(self.rfile.readline().decode('utf-8')))
		#Send headers
		self.send_header('Content-Length','0')
		self.send_header('Server','Fake yealink')
		self.end_headers()
		# Send message back to client
		#message = 'OK!'
		# Write content as utf-8 data
		#self.wfile.write(bytes(message, 'utf8'))
		
		#return

	def do_POST(self):
		global recievedPOSTstr
		self.send_response(200)
		recievedPOSTstr = self.rfile.readline().decode('utf-8')
		print('Recieved POST message: ' + recievedPOSTstr)
		#print('Recieved data: ' + str(self.rfile.readline().decode('utf-8')))
		#self.log_request()
		#Send headers
		self.request_version = 'HTTP/1.1'
		self.server_version = 'PY/1.0'

		self.send_header('Content-Length','0')
		#self.send_header('Server','Fake yealink')
		self.end_headers()
		#self.flush_headers()
		# Send message back to client
		#message = 'OK!'
		# Write content as utf-8 data
		#self.wfile.write(bytes(message, 'utf8'))
		#self.send_response(code=200, message='OK')


'''

print(host+':'+format(port))

client = paramiko.SSHClient()

client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print('Connecting to host: '+ host +' ...') 
'''

#client.connect(hostname=host, username=login, password=password, port=port)
colorama.init(autoreset=True)

def runHTTPYealinkListener():
	print('Starting Yealink http server...')
	# Server settings
	# Choose port 8080, for port 80, which is normally used for a http server, you need root access
	server_address = ('', 80)
	try:
		httpd = HTTPServer(server_address, testHTTPServer_RequestHandler)
	except Exception as e:
		print('Exception: ' + str(e))
	print('running yealink server...')
	httpd.serve_forever()


def ssActivate(dom=testingDomain):
	print('Activating services...')	

	if not ccn.ssAddAccessAll(dom=dom):
		return False
	#returnedFromSSH = executeOnSSH('cluster/storage/ds1/ss/access-list add ' + dom + ' *')
	#print(returnedFromSSH)

	if not ccn.ssEnable(dom=dom,subscrNum=masterNumber,ssNames='teleconference_manager chold ctr call_recording clip cnip'):
		return False
	if not ccn.ssEnable(dom=dom,subscrNum=secondaryMaster,ssNames='chold ctr call_recording cnip clip'):
		return False
	if not ccn.ssEnable(dom=dom,subscrNum=tcMembers,ssNames='chold ctr cnip clip'):
		return False
	
	if not ccn.ssActivation(dom=dom,subscrNum=secondaryMaster,ssName='chold',ssOptions='dtmf_sequence_as_flash = false'):
		return False
	if not ccn.ssActivation(dom=dom,subscrNum=secondaryMaster,ssName='ctr'):
		return False
	if not ccn.ssActivation(dom=dom,subscrNum=secondaryMaster,ssName='call_recording',ssOptions='mode = always_on'):
		return False

	if not ccn.ssActivation(dom=dom,subscrNum=masterNumber,ssName='chold',ssOptions='dtmf_sequence_as_flash = false'):
		return False
	if not ccn.ssActivation(dom=dom,subscrNum=masterNumber,ssName='call_recording',ssOptions='mode = always_on'):
		return False
	if not ccn.ssActivation(dom=dom,subscrNum=masterNumber,ssName='teleconference_manager',ssOptions='second_line = [' + secondaryMaster + ']'):
		return False

	if not ccn.ssActivation(dom=dom,subscrNum=tcMembers,ssName='cnip'):
		return False
	if not ccn.ssActivation(dom=dom,subscrNum=tcMembers,ssName='clip'):
		return False

	
	return True


def tcPhonesStatus(dom,masterNumber,exitOnFail=False,sysExitCode=1):
	print('Getting master Phones Status...')
	returnedFromSSH = ccn.executeOnSSH('domain/'+dom+'/tc/phones/status')
	print(returnedFromSSH)
	if masterNumber in returnedFromSSH:
		return True
	else:
		print('Master Number is not in tc master phones list')
		if exitOnFail:
			print('Exiting...')
			sys.exit(sysExitCode)		
		return False

def tcStartConf(dom,restHost,restPort,masterNumber,templateName):
	print('Trying to send start conference command...')
	try:
		r = requests.get('http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+masterNumber+'/choose')
	except Exception as e:
		print('Exception ocure in making http request: ' + format(e))
		return False
	if r.status_code != 200:
		print('Return code: ' + str(r.status_code))
		print
		return False
	XMLresult=r.content.decode('utf-8')[4:]  # cut 'xml='
	print('XML received: '+ XMLresult)
	try:
		XMLStruct = ET.fromstring(XMLresult)
	except Exception as e:
		print('Exception ocure in making structure: ' + format(e))
		return False		
	templateFound = False
	for element in XMLStruct.findall('MenuItem'):
		if templateName in element.find('Prompt').text:
			URLReq = element.find('URI').text
			templateFound = True
	if not templateFound:
		print('Didnt found such template ' + templateName)
		return False
	print('TC template start URL: ' + URLReq)

	r = requests.get(URLReq)
	if r.status_code != 200:
		print('Return code: ' + str(r.status_code))
		return False
	return True

def tcCancelPush(dom,restHost,restPort,Number):
	print('Pushing cancel button...')
	try:
		r = requests.get('http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+Number+'/cancel')
	except Exception as e:
		print('Exception ocure: ' + format(e))
		return False
	if r.status_code != 200:
		print('Return code: ' + str(r.status_code))
		return False
	return True

def tcExpPushOnUser(dom,restHost,restPort,masterNumber,memberNumber):
	print('Pushing on '+ str(memberNumber) +' member button ...')
	try:
		r = requests.get('http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+masterNumber+'/exp/'+memberNumber)
	except Exception as e:
		rint('Exception ocure: ' + format(e))
		return False
	if r.status_code != 200:
		print('Return code: ' + str(r.status_code))
		return False
	return True

def tcStopConf(dom,restHost,restPort,masterNumber):
	print('Pushing on stop conference...')
	if not tcCancelPush(dom=dom,restHost=restHost,restPort=restPort,Number=masterNumber):
		return False
	time.sleep(0.5)

	if tcExpPushOnUser(dom=dom,restHost=restHost,restPort=restPort,masterNumber=masterNumber,memberNumber=masterNumber):
		return True
	else:
		return False

def tcCancelUser(dom,restHost,restPort,Number):
	if not tcCancelPush(dom=dom,restHost=restHost,restPort=restPort,Number=masterNumber):
		return False
	time.sleep(0.5)
	if tcExpPushOnUser(dom=dom,restHost=restHost,restPort=restPort,masterNumber=masterNumber,memberNumber=Number):
		return True
	else:
		return False

def tcGroupAll(dom,restHost,restPort,masterNumber):
	print('Trying to send tc group call...')
	try:
		r = requests.get('http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+masterNumber+'/group/all')
	except Exception as e:
		rint('Exception ocure: ' + format(e))
		return False
	if r.status_code != 200:
		print('Return code: ' + str(r.status_code))
		return False
	return True


#############################################################################################

def preconfigure():
	cnt=0
	ctx= """<context domain=\""""+ testingDomain +"""\" digitmap="auto" name=\""""+ tcRoutingName+ """\">
    <rule name="tc">
    <conditions>
       <cdpn digits=\""""+ masterNumber +"""\"/>
    </conditions>
    <result>
       <teleconference/>
     </result>
    </rule>
    <rule name="toSIPpTrunk">
     <conditions>
       <cdpn digits=\""""+ tcClientNumberPrefix +"""%\"/>
     </conditions>
     <result>
        <external>
          <trunk value=\""""+tcExtTrunkName+"""\"/>
        </external>
     </result>
    </rule>
    <rule name="local_calls">
     <conditions>
       <cdpn digits="%"/>
     </conditions>
     <result>
        <local/>
     </result>
    </rule>
</context>"""

	###### - to be removed
	hRequests = HT.httpTerm(host=host,port='9999',login=login,passwd=password)

	if ccn.domainDeclare(testingDomain) :
		print(Fore.GREEN + 'Successful domain declare')
	else :
		print(Fore.RED + 'Smthing happen wrong with domain declaration...')
		return False

	cnt = 0
	time.sleep(2)
	while not ccn.checkDomainInit(testingDomain):					# проверяем инициализацию домена
		print(Fore.YELLOW + 'Not inited yet...')	
		cnt += 1
		if cnt > 5:
			print(Fore.RED + "Test domain wasn't inited :(")
			return False
			#sys.exit(1)
		time.sleep(2)

	if ccn.sipTransportSetup(dom=testingDomain,sipIP=testingDomainSIPaddr,sipPort=testingDomainSIPport):
		print(Fore.GREEN + 'Successful SIP transport declare')
	else :
		print(Fore.RED + 'Smthing happen wrong with SIP network setup...')
		return False
		#sys.exit(1)

	if hRequests.routeCtxAdd(domainName=testingDomain,ctxString=ctx) == 201:
		print(Fore.GREEN + 'Successful declaration routing CTX')
	else:
		print(Fore.RED + 'Smthing happen wrong with routing declaration...')
	#time.sleep(5)

	if ccn.subscribersCreate(dom=testingDomain,sipNumber=masterNumber,sipPass=masterSIPpass,sipGroup=SIPgroup,routingCTX=tcRoutingName):
	 	print(Fore.GREEN + 'Successful Master creation')
	else:
		print(Fore.RED + 'Smthing happen wrong with subscribers creation...')
		return False

	if ccn.subscribersCreate(dom=testingDomain,sipNumber=secondaryMaster,sipPass=secondaryMaster,sipGroup=SIPgroup,routingCTX=tcRoutingName):
	 	print(Fore.GREEN + 'Successful Secondary Master creation')
	else:
		print(Fore.RED + 'Smthing happen wrong with subscriber creation...')
		return False

	if ccn.subscribersCreate(dom=testingDomain,sipNumber=tcMembers,sipPass='1234',sipGroup=SIPgroup,routingCTX=tcRoutingName):
	 	print(Fore.GREEN + 'Successful Members creation')
	else:
		print(Fore.RED + 'Smthing happen wrong with subscribers creation...')
		return False
		#sys.exit(1)

	if ccn.setLogging(node=coreNode,logRule='all_tc',action='on'):
	 	print(Fore.GREEN + 'Logging of '+coreNode+ ' all_tc switched to on')
	else:
		print(Fore.RED + 'Smthing happen wrong with logging switching...')

	if ccn.setTraceMode(dom=testingDomain,traceMode='full_compressed'):
		print(Fore.GREEN + 'core traces successfully enabled')
	else:
		print(Fore.RED + 'Smthing happen wrong with changing core trace mode...')


	if ssActivate(testingDomain):
		print(Fore.GREEN + 'Successful Services activated for all subscribers')
	else:
		print(Fore.RED + 'Smthing happen wrong activating services...')
		return False
		#sys.exit(1)

	if ccn.setSysIfaceRoutung(dom=testingDomain,sysIface='system:teleconference',routingCTX=tcRoutingName):
		print(Fore.GREEN + 'Successful set routing for sys:teleconference')
	else:
		print(Fore.RED + 'Smthing happen wrong with set routing for sys:teleconference')
		return False
		sys.exit(1)


	if ccn.trunkDeclare(dom=testingDomain,trunkName=tcExtTrunkName,trunkGroup='test.trunk',routingCTX=tcRoutingName,sipPort=testingDomainSIPport,sipIPset='ipset',destSipIP=tcExtTrunkIP,destSipPort=tcExtTrunkPort):
		print(Fore.GREEN + 'Successful SIP trunk declare')
	else:
		print(Fore.RED + 'Smthing happen wrong with SIP trunk declaration')
		return False
		#sys.exit(1)

	if ccn.tcRestHostSet(restHost=restHost,restPort=restPort):
		print(Fore.GREEN + 'Successful restHost set')
	else:
		print(Fore.RED + 'Smthing happen wrong with restHost set')
		return False
		#sys.exit(1)

	tcPhonesStatus(dom=testingDomain,masterNumber=masterNumber)

	#time.sleep(1)
	#if hRequests.tcTemplateCreate(testingDomain,templateName=testTemplateName,addressFirst=tcClientNumberPrefix+'00',addressesCount=int(tcClientCount)) == 201:
	if hRequests.tcTemplateCreate(testingDomain,templateName=testTemplateName,addressFirst='2001',addressesCount=tcUACCount) == 201:
		print(Fore.GREEN + 'Successful teleconference template creation')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference template creation...')
		return False
		#sys.exit(1)

	return True

	'''
	print('Generating csv file...')
	output = subprocess.Popen([tcPath+'/csv_generate.sh', tcPath+'/master.csv', masterNumber, '1', testingDomain], stdout=subprocess.PIPE)
	#output = subprocess.Popen(['ifconfig'], stdout=subprocess.PIPE)
	print(output.stdout.read().decode('utf-8'))
	time.sleep(0.1)

	output.poll()  # get usbprocess status
	if output.returncode == 0 :
		print(Fore.GREEN + 'Successful CSV generation')
	else:
		print(Fore.RED + 'Smthing happen wrong with CSV generation...')
		return False
		#sys.exit(1)

	'''
	###### - to be removed
	#'''

def basicTest():
	Failure = False
	global tcMasterUA
	global tcUAcli

	'''
	if tcExtTrunkIP in '192.168.118.12':  # для меня
		print('Script in running on my PC')
		sippListenAddress='192.168.118.12'
	'''
	#sippResgistrer = subprocess.Popen([sippPath, testingDomainSIPaddr+':'+testingDomainSIPport, '-sf', tcPath+'/reg-int.xml', '-m', '1', '-l', '1', '-p', sippListenPort, '-i', sippListenAddress, '-inf', tcPath+'/master.csv', '-trace_screen'], stdout=subprocess.PIPE)   # запускаем сип регистратор мастера
	tcMasterUA = pjua.SubscriberUA(domain=testingDomain,username=masterNumber,passwd=masterSIPpass,sipProxy=testingDomainSIPaddr+':'+testingDomainSIPport,displayName='TC Master UA',uaIP=sippListenAddress,regExpiresTimeout=60)
	

	tcUAcli = []

	for i in range(1, tcUACCount+1):
		subscrNum = str(2000+i)
		tcUAcli.append(pjua.SubscriberUA(domain=testingDomain,username=subscrNum,passwd='1234',sipProxy=testingDomainSIPaddr+':'+testingDomainSIPport,displayName='Test UA'+str(i),uaIP=sippListenAddress,regExpiresTimeout=60))
		#print('Len =' + str(len(tcUAcli)) )


	if tcMasterUA.uaAccountInfo.reg_status != 200:
		print(Fore.RED + 'Master UA failed to register!')
		print(str(tcMasterUA.uaAccountInfo.uri) + ' state: ' + str(tcMasterUA.uaAccountInfo.reg_status) + ' - ' + str(tcMasterUA.uaAccountInfo.reg_reason))
		return False
		#sys.exit(1)

	print(Fore.GREEN + 'Master UA Registered')

	allCliRegistered = False
	cnt = 0
	while not allCliRegistered:
		if cnt > 50:		
			print(Fore.RED + 'Some client UAs failed to register!')
			for i in range(0,tcUACCount):
				print(str(tcUAcli[i].uaAccountInfo.uri) + ' state: ' + str(tcUAcli[i].uaAccountInfo.reg_status) + ' - ' + str(tcUAcli[i].uaAccountInfo.reg_reason))
			return False
			#sys.exit(1)
		cnt += 1
		time.sleep(0.1)
		for i in range(0,tcUACCount):
			print('.', end='')
			if tcUAcli[i].uaAccountInfo.reg_status != 200:
				allCliRegistered = False
				break
			else:
				allCliRegistered = True
	print('\n')
	print(Fore.GREEN + 'All UAC registered...')

	ccn.subscriberSipInfo(dom=testingDomain,sipNumber=masterNumber,sipGroup=SIPgroup,complete=False)

	if tcStartConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,templateName=testTemplateName):
		print(Fore.GREEN +'Start teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference starting...')
		return False
		#sys.exit(1)

	time.sleep(5)

	if tcMasterUA.uaCurrentCallInfo.state != 5:
		print(Fore.RED + 'Master UA is in wrong state')
		return False
		#sys.exit(1)
	else:
		print(Fore.GREEN + 'Master UA is in active call state')


	print(Style.BRIGHT + 'Connecting user one by one')
	for num in range(2001, 2001 + tcUACCount):
		if tcExpPushOnUser(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,memberNumber=str(num)):
			print(Fore.GREEN +'User '+ str(num) +' command sent')
		else:
			print(Fore.RED + 'Smthing happen wrong with sending user '+ str(num) +' command sent...')
			#return False

	print(Style.BRIGHT + 'Teleconference in progress.... ')
	cnt=0 # timer
	confDuration = 10 + (tcUACCount * 2)

	while cnt < confDuration:		
		time.sleep(1)
		print('.',end='')
		cnt += 1
		for i in range(0,tcUACCount):
			if tcUAcli[i].uaCurrentCallInfo.state != 5:
				print(Fore.YELLOW +'UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)


	print(Style.BRIGHT + 'Releasing use by it self')
	for i in range(0,tcUACCount):	
		tcUAcli[i].uaCurrentCall.hangup(code=200, reason='Release')

	time.sleep(1)

	if tcMasterUA.uaCurrentCallInfo.state != 5:
		print(Fore.RED + 'Master UA is in wrong state')
		print(Fore.YELLOW +'Master UA in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		#return False
		#sys.exit(1)
	else:
		print(Fore.GREEN + 'Master UA still in conference - it is ok. Continue...')


	print('Making group call...')
	if tcGroupAll(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Group call command sent')
	else:
		print(Fore.RED + 'Smthing happen wrong with sending a group call command...')
		return False
		#sys.exit(1)	

	print(Style.BRIGHT + 'Teleconference in progress.... ')

	cnt=0 # timer
	confDuration = 10 + (tcUACCount * 2)

	while cnt < confDuration:		
		time.sleep(1)
		print('.',end='')
		cnt += 1
		for i in range(0,tcUACCount):
			if tcUAcli[i].uaCurrentCallInfo.state != 5:
				print(Fore.YELLOW +'UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
	'''
	tcMasterUA.uaCurrentCall.hold()
	time.sleep(1)
	tcMasterUA.uaCurrentCall.unhold()
	'''

	print(Style.BRIGHT + 'Stoping teleconference....')
	if tcStopConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Stop teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference stoping...')
		return False
		#sys.exit(1)	

	time.sleep(5)

	UAnotReleased = False
	if tcMasterUA.uaCurrentCallInfo.state != 6:
		print(Fore.RED + 'Master UA is in wrong state')
		print(Fore.YELLOW +'Master UA in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		#return False
		#sys.exit(1)
	else:
		print(Fore.GREEN + 'Master UA successfully released')

	for i in range(0,tcUACCount):
		if tcUAcli[i].uaCurrentCallInfo.state != 6:
			print(Fore.YELLOW +'UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			UAnotReleased = True

	if UAnotReleased:
		print(Fore.RED + 'Some UAs didnt disconected')
		return False
		#sys.exit(1)
	else:
		print(Fore.GREEN +'All UA successfully released')
		return True
	return True

def riseForVoice():
	global tcMasterUA
	global tcUAcli
	global recievedPOSTstr

	if tcStartConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,templateName=testTemplateName):
		print(Fore.GREEN +'Start teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference starting...')
		return False
		#sys.exit(1)

	time.sleep(2)

	if tcMasterUA.uaCurrentCallInfo.state != 5:
		print(Fore.RED + 'Master UA is in wrong state')
		return False
		#sys.exit(1)
	else:
		print(Fore.GREEN + 'Master UA is in active call state')


	print('Making group call...')
	if tcGroupAll(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Group call command sent')
	else:
		print(Fore.RED + 'Smthing happen wrong with sending a group call command...')
		return False
		#sys.exit(1)	

	time.sleep(1)

	for i in range(0,tcUACCount):
		if tcUAcli[i].uaCurrentCallInfo.state != 5:
			print(Fore.YELLOW +'UA '+ str(i) + ' in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)


	print(Style.BRIGHT + 'Teleconference in progress.... ')

	cnt=0 # timer
	confDuration = 10 + (tcUACCount * 2)

	#time.sleep(2)
	
	voiceOnNotifyRecieved = False
	voiceOnBlinkLedRecieved = False
	while cnt < confDuration:		
		time.sleep(1)
		print('.',end='')
		cnt += 1
		if cnt == 6:
			print(Style.BRIGHT +'Sending DTMF...')
			tcUAcli[0].sendInbandDTMF(dtmfDigit='1')
		if cnt > 6:
			if '<Title>2001</Title><Text>Дайте мне голос, пожалуйста</Text>' in  recievedPOSTstr:
				voiceOnNotifyRecieved = True
			if 'Led: EXP-1-1-GREEN=fastflash' in recievedPOSTstr:
				voiceOnBlinkLedRecieved = True
		for i in range(0,tcUACCount):
			if tcUAcli[i].uaCurrentCallInfo.state != 5:
				print(Fore.YELLOW +'UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)

	
	print(Style.BRIGHT + 'Stoping teleconference....')
	if tcStopConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Stop teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference stoping...')
		return False
		#sys.exit(1)	

	time.sleep(5)

	UAnotReleased = False
	if tcMasterUA.uaCurrentCallInfo.state != 6:
		print(Fore.RED + 'Master UA is in wrong state')
		print('Master UA in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		#return False
		#sys.exit(1)
	else:
		print(Fore.GREEN + 'Master UA successfully released')

	for i in range(0,tcUACCount):
		if tcUAcli[i].uaCurrentCallInfo.state != 6:
			print('UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			UAnotReleased = True

	if not voiceOnNotifyRecieved:
		print(Fore.RED + 'Didnt recieved Notify message ')
		return False
	else:
		print(Fore.GREEN + 'Voice on notify message successful recieved')

	if not voiceOnBlinkLedRecieved:
		print(Fore.RED + 'LED indicator didnt blinked on voice notification')
		return False
	else:
		print(Fore.GREEN + 'LED indicator successful changed on voice notification')


	if UAnotReleased:
		print(Fore.RED + 'Some UAs didnt disconected')
		return False
		#sys.exit(1)
	else:
		print(Fore.GREEN +'All UA successfully released')		

	return True

def connectToConfViaTransfer():
	global tcMasterUA
	global tcUAcli
	global extUAcli
	global tcSecondaryMasterUA

	tcSecondaryMasterUA = pjua.SubscriberUA(domain=testingDomain,username=secondaryMaster,passwd=secondaryMaster,sipProxy=testingDomainSIPaddr+':'+testingDomainSIPport,displayName='TC Secondary Master UA',uaIP=sippListenAddress,regExpiresTimeout=60)
	extUAcli = pjua.SubscriberUA(domain=testingDomain,username=tcExtMember,passwd='1234',sipProxy=testingDomainSIPaddr+':'+testingDomainSIPport,displayName='TC ext UA',uaIP=sippListenAddress,regExpiresTimeout=60)

	if tcMasterUA.uaAccountInfo.reg_status != 200:
		print(Fore.RED + 'Master UA failed to register!')
		print(str(tcMasterUA.uaAccountInfo.uri) + ' state: ' + str(tcMasterUA.uaAccountInfo.reg_status) + ' - ' + str(tcMasterUA.uaAccountInfo.reg_reason))
		return False

	if tcSecondaryMasterUA.uaAccountInfo.reg_status != 200:
		print(Fore.RED + 'Secondary Master UA failed to register!')
		print(str(tcMasterUA.uaAccountInfo.uri) + ' state: ' + str(tcMasterUA.uaAccountInfo.reg_status) + ' - ' + str(tcMasterUA.uaAccountInfo.reg_reason))
		return False

	if extUAcli.uaAccountInfo.reg_status != 200:
		print(Fore.RED + 'Client UA failed to register!')
		print(str(tcMasterUA.uaAccountInfo.uri) + ' state: ' + str(tcMasterUA.uaAccountInfo.reg_status) + ' - ' + str(tcMasterUA.uaAccountInfo.reg_reason))
		return False


	if tcStartConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,templateName=testTemplateName):
		print(Fore.GREEN +'Start teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference starting...')
		return False
		#sys.exit(1)

	time.sleep(3)

	if tcMasterUA.uaCurrentCallInfo.state != 5:
		print(Fore.RED + 'Master UA is in wrong state')
		return False
		#sys.exit(1)
	else:
		print(Fore.GREEN + 'Master UA is in active call state')


	tcMasterUA.uaCurrentCall.hold()
	time.sleep(1)

	tcSecondaryMasterUA.makeCall(phoneURI=tcExtMember+'@'+testingDomain)

	print('waiting for answer...')
	cnt = 0
	Answered = False
	while cnt < 50:		
		time.sleep(0.1)
		if tcSecondaryMasterUA.uaCurrentCallInfo.state == 5:
			Answered = True
			break			
		print('.',end='')		
		cnt += 1

	if not Answered:
		print('Call not recieved')
		return False
	else:
		print('Call answered')

	#tcSecondaryMasterUA.uaCurrentCall.transfer(dest_uri='sip:'+masterNumber+'@'+testingDomain)
	#print('holding...')
	#tcSecondaryMasterUA.uaCurrentCall.hold()
	time.sleep(2)
	print('transfering...')

	tcSecondaryMasterUA.ctr_request(dstURI=masterNumber+'@'+testingDomain)
	time.sleep(1)
	print('hanging up...')
	tcSecondaryMasterUA.uaCurrentCall.hangup(code=200, reason='Release after transfer')

	cnt = 0
	Released = False
	while cnt < 50:		
		time.sleep(0.1)
		if tcSecondaryMasterUA.uaCurrentCallInfo.state == 6:
			Released = True
			break			
		print('.',end='')
		cnt += 1

	if not Released:
		print(Fore.RED +'Secondary Master call not released')
		return False
	else:
		print(Fore.GREEN +'Secondary Master released after transfer')

	time.sleep(1)

	#tcSecondaryMasterUA
	print('Unholding master...')
	tcMasterUA.uaCurrentCall.unhold()

	cnt=0 # timer
	confDuration = 10 

	while cnt < confDuration:		
		time.sleep(1)
		print('.',end='')
		cnt += 1
		if extUAcli.uaCurrentCallInfo.state != 5:
			print(Fore.YELLOW +'Client UA '+ str(i) + ' still in wrong state: ' + str(extUAcli.uaAccountInfo.uri) + ' ' + extUAcli.uaCurrentCallInfo.state_text)
		if tcMasterUA.uaCurrentCallInfo.state != 5:
			print(Fore.YELLOW +'Master UA '+ str(i) + ' still in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)

	print('Stoping teleconference....')
	if tcStopConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Stop teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference stoping...')
		return False
		#sys.exit(1)	

	time.sleep(5)

	UAnotReleased = False
	if extUAcli.uaCurrentCallInfo.state != 6:
		print(Fore.YELLOW +'Client UA '+ str(i) + ' still in wrong state: ' + str(extUAcli.uaAccountInfo.uri) + ' ' + extUAcli.uaCurrentCallInfo.state_text)
		UAnotReleased = True
	else:
		print(Fore.GREEN +'Client UA Released')

	if tcMasterUA.uaCurrentCallInfo.state != 6:
		print(Fore.YELLOW +'Master UA '+ str(i) + ' still in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		UAnotReleased = True
	else:
		print(Fore.GREEN +'Master UA Released')


	if UAnotReleased:
		print(Fore.RED + 'Some UAs didnt disconected')
		return False
		#sys.exit(1)
	else:
		print(Fore.GREEN +'All UA successfully released')
		return True
	return True

#############################################################################################

tcMasterUA = 0
tcUAcli = 0

#'''
print('-Start preconfiguration test-')
if not preconfigure():
	print(Fore.RED + 'Preconfiguration test failed')
	sys.exit(1)
else:
	print('-Start preconfiguration done!-')
	time.sleep(1)
#'''


httpYealinkListen_T = Thread(target=runHTTPYealinkListener, name='httpYealinkListen', daemon=True)
#httpYealinkListen_T.daemon = True 
httpYealinkListen_T.start()

#runHTTPYealinkListener()

print(Style.BRIGHT +'-Starting basic test-')
if not basicTest():
	print(Fore.RED + 'Basic test failed')
	sys.exit(1)
else:
	print(Fore.GREEN +'-Basic test done!-')
	time.sleep(1)

print(Style.BRIGHT +'-Starting request for voice test-')
if not riseForVoice():
	print(Fore.RED + 'Request for voice failed')
	sys.exit(1)
else:
	print(Fore.GREEN +'Request for voice test done!-')
	time.sleep(1)

print(Style.BRIGHT +'-Starting connection to active conference test-')
if not connectToConfViaTransfer():
	print(Fore.RED + 'Connect via transfer test failed')
	sys.exit(1)
else:
	print(Fore.GREEN +'-Connection to active conference test done!-')
	time.sleep(1)

print(Fore.GREEN +'It seems to be all FINE...')
print('We did it!!')
sys.exit(0)