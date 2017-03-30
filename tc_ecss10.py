#!/usr/local/bin/python3.5

import config, time, sys, colorama, requests, logging
#import subprocess
import hc_module.ecss_config_http_commands as HT
from colorama import Fore, Back, Style
import xml.etree.ElementTree as ET
import signal
import pjSIP_py.pjUA as pjua
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import ssh_cocon.ssh_cocon as ccn

testingDomain = config.testConfigJson['DomainName']
testingDomainSIPport = config.testConfigJson['sipListenPort']
testingDomainSIPaddr = config.testConfigJson['SystemVars'][0]['%%EXTER_IP%%']
testingDomainSIPaddr2 = config.testConfigJson['SystemVars'][0]['%%EXTER_IP2%%']

#sippPath = str(os.environ.get('SIPP_PATH'))
pjListenAddress=config.testConfigJson['SystemVars'][0]['%%IP%%']
pjListenPort=config.testConfigJson['SIPuaListenPort']
sippMediaListenPort='16016'
sippMediaListenPortTrunk='17016'

masterNumber = config.testConfigJson['UsersMasters'][0]['Number']
secondaryMaster = config.testConfigJson['UsersMasters'][1]['Number']
masterSIPpass = config.testConfigJson['UsersMasters'][0]['Password']
SIPgroup = config.testConfigJson['UsersMasters'][0]['SipGroup']
restHost = config.testConfigJson['SystemVars'][0]['%%EXTER_IP%%']
restPort = config.testConfigJson['RestPort']
testTemplateName = config.testConfigJson['TemplateName']

#tcPath = str(os.environ.get('TC_PATH'))
tcRoutingName = 'test_tc'
tcExtTrunkName = 'toSIPp'
#tcExtTrunkIP=str(os.environ.get('TC_EXT_TRUNK_IP'))
#tcExtTrunkPort=str(os.environ.get('TC_EXT_TRUNK_PORT'))
#tcClientCount=str(os.environ.get('TC_CLIENT_COUNT'))
tcClientNumberPrefix = config.testConfigJson['UsersClients'][0]['Number'][0]
tcUACCount = len(config.testConfigJson['UsersClients'])
#tcUAcliCount = 5
tcMembers = '{' + config.testConfigJson['UsersClients'][0]['Number'] + '-' + config.testConfigJson['UsersClients'][tcUACCount-1]['Number'] + '}'
tcExtMember = config.testConfigJson['UsersExternal'][0]['Number']

tcMasterUA = None
tcUAcli = []
extUAcli = None
tcSecondaryMasterUA = None

recievedPOSTstr = ''
testResultsList = []

colorama.init(autoreset=True)
'''
class YeaPhone():
	def __init__():
		pass
	def parseXML():
		pass
'''

# HTTPRequestHandler class
class testHTTPServer_RequestHandler(BaseHTTPRequestHandler):
 
# GET
	def do_GET(self):
		# Send response status code
		self.send_response(200)
		print('Recieved GET message')
		logging.info('Recieved GET message')
		logging.info('Recieved data: ' + str(self.rfile.readline().decode('utf-8')))
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
		print('Recieved POST message')
		logging.info('Recieved POST message: ' + recievedPOSTstr)
		#logging.info('Recieved data: ' + str(self.rfile.readline().decode('utf-8')))
		#print('Recieved POST message: ' + recievedPOSTstr)
		#print('Recieved data: ' + str(self.rfile.readline().decode('utf-8')))
		#self.log_request()
		#Send headers
		self.request_version = 'HTTP/1.1'
		self.server_version = 'PY/1.0'

		self.send_header('Content-Length','0')
		self.send_header('Server','Fake Yealink')
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

def runHTTPYealinkListener():
	print('Starting Yealink http server...')
	# Server settings
	# Choose port 8080, for port 80, which is normally used for a http server, you need root access
	server_address = ('', 80)
	try:
		httpd = HTTPServer(server_address, testHTTPServer_RequestHandler)
		logging.info('Starting running http fake Yealink server')
	except Exception as e:
		print('Exception: ' + str(e))
		logging.error('Exception happen at http server start: ' + str(e))
	print('running yealink server...')
	httpd.serve_forever()


def ssActivate(dom=testingDomain):
	print('Activating services...')	

	if not ccn.ssAddAccessAll(dom=testingDomain):
		return False
	#returnedFromSSH = executeOnSSH('cluster/storage/ds1/ss/access-list add ' + dom + ' *')
	#print(returnedFromSSH)

	if not ccn.ssEnable(dom=testingDomain,subscrNum=masterNumber,ssNames='teleconference_manager chold ctr call_recording clip cnip'):
		return False
	if not ccn.ssEnable(dom=testingDomain,subscrNum=secondaryMaster,ssNames='chold ctr call_recording cnip clip'):
		return False
	if not ccn.ssEnable(dom=testingDomain,subscrNum=tcMembers,ssNames='chold ctr cnip clip'):
		return False
	
	if not ccn.ssActivation(dom=testingDomain,subscrNum=secondaryMaster,ssName='chold',ssOptions='dtmf_sequence_as_flash = false'):
		return False
	if not ccn.ssActivation(dom=testingDomain,subscrNum=secondaryMaster,ssName='ctr'):
		return False
	if not ccn.ssActivation(dom=testingDomain,subscrNum=secondaryMaster,ssName='call_recording',ssOptions='mode = always_on'):
		return False

	if not ccn.ssActivation(dom=testingDomain,subscrNum=masterNumber,ssName='chold',ssOptions='dtmf_sequence_as_flash = false'):
		return False
	if not ccn.ssActivation(dom=testingDomain,subscrNum=masterNumber,ssName='call_recording',ssOptions='mode = always_on'):
		return False
	if not ccn.ssActivation(dom=testingDomain,subscrNum=masterNumber,ssName='teleconference_manager',ssOptions='second_line = [' + secondaryMaster + ']'):
		return False

	if not ccn.ssActivation(dom=testingDomain,subscrNum=tcMembers,ssName='cnip'):
		return False
	if not ccn.ssActivation(dom=testingDomain,subscrNum=tcMembers,ssName='clip'):
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
	logging.info('Trying to send start conference command...')
	try:
		logging.info('Http request: ' + 'http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+masterNumber+'/choose')
		r = requests.get('http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+masterNumber+'/choose')
	except Exception as e:
		print('Exception ocure in making http request: ' + format(e))
		logging.error('Exception ocure in making http request: ' + format(e))
		return False
	if r.status_code != 200:
		print('Return code: ' + str(r.status_code))
		logging.info('Return code: ' + str(r.status_code))
		return False
	XMLresult=r.content.decode('utf-8')[4:]  # cut 'xml='
	print('XML received: '+ XMLresult)
	logging.info('XML received: '+ XMLresult)
	try:
		XMLStruct = ET.fromstring(XMLresult)
	except Exception as e:
		print('Exception ocure in making structure: ' + format(e))
		logging.error('Exception ocure in making structure: ' + format(e))
		return False		
	templateFound = False
	for element in XMLStruct.findall('MenuItem'):
		if templateName in element.find('Prompt').text:
			URLReq = element.find('URI').text
			templateFound = True
	if not templateFound:
		print('Didnt found such template ' + templateName)
		logging.error('Didnt found such template ' + templateName)
		return False
	print('TC template start URL: ' + URLReq)
	logging.info('TC template start URL: ' + URLReq)

	r = requests.get(URLReq)
	if r.status_code != 200:
		print('Return code: ' + str(r.status_code))
		logging.error('Return code: ' + str(r.status_code))
		return False
	logging.info('Return code: ' + str(r.status_code))
	return True

def tcCancelPush(dom,restHost,restPort,Number):
	print('Pushing cancel button...')
	logging.info('Pushing cancel button...')
	try:
		logging.info(
			'Http request: ' + 'http://' + restHost + ':' + restPort + '/' + dom + '/service/tc/' + masterNumber + '/choose')
		r = requests.get('http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+Number+'/cancel')
	except Exception as e:
		print('Exception ocure: ' + format(e))
		logging.error('Exception ocure: ' + format(e))
		return False
	if r.status_code != 200:
		logging.error('Return code: ' + str(r.status_code))
		print('Return code: ' + str(r.status_code))
		return False
	logging.info('Return code: ' + str(r.status_code))
	return True

def tcExpPushOnUser(dom,restHost,restPort,masterNumber,memberNumber):
	print('Pushing on '+ str(memberNumber) +' member button ...')
	logging.info('Pushing on '+ str(memberNumber) +' member button ...')
	try:
		logging.info('http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+masterNumber+'/exp/'+memberNumber)
		r = requests.get('http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+masterNumber+'/exp/'+memberNumber)
	except Exception as e:
		print('Exception ocure: ' + format(e))
		logging.error('Exception ocure: ' + format(e))
		return False
	if r.status_code != 200:
		logging.error('Return code: ' + str(r.status_code))
		print('Return code: ' + str(r.status_code))
		return False
	logging.info('Return code: ' + str(r.status_code))
	return True

def tcStopConf(dom,restHost,restPort,masterNumber):
	print('Pushing on stop conference...')
	logging.info('Pushing on stop conference...')
	if not tcCancelPush(dom=dom,restHost=restHost,restPort=restPort,Number=masterNumber):
		return False
	time.sleep(0.5)
	if tcExpPushOnUser(dom=dom,restHost=restHost,restPort=restPort,masterNumber=masterNumber,memberNumber=masterNumber):
		return True
	else:
		return False

def tcCancelUser(dom,restHost,restPort,Number):
	print('Pushing on cancel user from conference...')
	logging.info('Pushing on cancel user from conference...')
	if not tcCancelPush(dom=dom,restHost=restHost,restPort=restPort,Number=masterNumber):
		return False
	time.sleep(0.5)
	if tcExpPushOnUser(dom=dom,restHost=restHost,restPort=restPort,masterNumber=masterNumber,memberNumber=Number):
		return True
	else:
		return False

def tcGroupAll(dom,restHost,restPort,masterNumber):
	print('Trying to send tc group call...')
	logging.info('Trying to send tc group call...')
	try:
		logging.info(
			'Http request: ' + 'http://' + restHost + ':' + restPort + '/' + dom + '/service/tc/' + masterNumber + '/choose')
		r = requests.get('http://'+restHost+':'+restPort+'/'+dom+'/service/tc/'+masterNumber+'/group/all')
	except Exception as e:
		print('Exception ocure: ' + format(e))
		logging.error('Exception ocure: ' + format(e))
		return False
	if r.status_code != 200:
		logging.info('Return code: ' + str(r.status_code))
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
	hRequests = HT.httpTerm(host=config.host,port='9999',login=config.login,passwd=config.password)

	if ccn.domainDeclare(testingDomain, removeIfExists = False) :
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
	if ccn.sipTransportSetup(dom=testingDomain,sipIP=testingDomainSIPaddr2,sipPort=testingDomainSIPport, sipNode='sip1@ecss2'):
		print(Fore.GREEN + 'Successful secondary SIP transport declare')
	else :
		print(Fore.YELLOW + 'Smthing happen wrong with secondary SIP network setup...')

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

	if ccn.subscribersCreate(dom=testingDomain,sipNumber=tcMembers,sipPass=masterSIPpass,sipGroup=SIPgroup,routingCTX=tcRoutingName):
		print(Fore.GREEN + 'Successful Members creation')
	else:
		print(Fore.RED + 'Smthing happen wrong with subscribers creation...')
		return False

	if ccn.subscribersCreate(dom=testingDomain,sipNumber=tcExtMember,sipPass=masterSIPpass,sipGroup=SIPgroup,routingCTX=tcRoutingName):
		print(Fore.GREEN + 'Successful External subscriber creation')
	else:
		print(Fore.RED + 'Smthing happen wrong with subscriber creation...')
		return False

	if ccn.setLogging(node=config.coreNode,logRule='all_tc_bin',action='on'):
		print(Fore.GREEN + 'Logging of '+ config.coreNode+ ' all_tc switched to on')
	else:
		print(Fore.RED + 'Smthing happen wrong with logging switching...')

	if ccn.setTraceMode(dom=testingDomain,traceMode='full_compressed'):
		print(Fore.GREEN + 'core traces successfully enabled')
	else:
		print(Fore.RED + 'Smthing happen wrong with changing core trace mode...')


	if ssActivate():
		print(Fore.GREEN + 'Successful Services activated for all subscribers')
	else:
		print(Fore.RED + 'Smthing happen wrong activating services...')
		return False

	if ccn.setSysIfaceRoutung(dom=testingDomain,sysIface='system:teleconference',routingCTX=tcRoutingName):
		print(Fore.GREEN + 'Successful set routing for sys:teleconference')
	else:
		print(Fore.RED + 'Smthing happen wrong with set routing for sys:teleconference')
		return False
	'''
	if ccn.trunkDeclare(dom=testingDomain,trunkName=tcExtTrunkName,trunkGroup='test.trunk',routingCTX=tcRoutingName,sipPort=testingDomainSIPport,sipIPset='ipset',destSipIP=tcExtTrunkIP,destSipPort=tcExtTrunkPort):
		print(Fore.GREEN + 'Successful SIP trunk declare')
	else:
		print(Fore.RED + 'Smthing happen wrong with SIP trunk declaration')
		return False
	'''

	if ccn.tcRestHostSet(restHost=restHost,restPort=restPort):
		print(Fore.GREEN + 'Successful restHost set')
	else:
		print(Fore.RED + 'Smthing happen wrong with restHost set')
		return False

	tcPhonesStatus(dom=testingDomain,masterNumber=masterNumber)

	#time.sleep(1)
	#if hRequests.tcTemplateCreate(testingDomain,templateName=testTemplateName,addressFirst=tcClientNumberPrefix+'00',addressesCount=int(tcClientCount)) == 201:
	if hRequests.tcTemplateCreate(testingDomain,templateName=testTemplateName,addressFirst=str(int(config.testConfigJson['UsersClients'][0]['Number'])),
								  addressesCount=tcUACCount) == 201:
		print(Fore.GREEN + 'Successful teleconference template creation')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference template creation...')
		#return False

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

def registerUAs():
	logging.info('Creating pj subscribers')
	global tcMasterUA
	global tcSecondaryMasterUA
	global extUAcli
	global tcMasterUA

	tcMasterUA = pjua.SubscriberUA(domain=testingDomain,username=masterNumber,passwd=masterSIPpass,sipProxy=testingDomainSIPaddr+':'+testingDomainSIPport,
								   displayName='TC Master UA',uaIP=pjListenAddress,regExpiresTimeout=300)
	tcSecondaryMasterUA = pjua.SubscriberUA(domain=testingDomain,username=secondaryMaster,passwd=secondaryMaster,sipProxy=testingDomainSIPaddr+':'+testingDomainSIPport,
											displayName='TC Secondary Master UA',uaIP=pjListenAddress,regExpiresTimeout=300)
	extUAcli = pjua.SubscriberUA(domain=testingDomain,username=tcExtMember,passwd=masterSIPpass,sipProxy=testingDomainSIPaddr+':'+testingDomainSIPport,
								 displayName='TC ext UA',uaIP=pjListenAddress,regExpiresTimeout=300)

	for i in range(tcUACCount):
		subscrNum = config.testConfigJson['UsersClients'][i]['Number']
		tcUAcli.append(pjua.SubscriberUA(domain=testingDomain,username=subscrNum,passwd=masterSIPpass,sipProxy=testingDomainSIPaddr+':'+testingDomainSIPport,
										 displayName='Test UA'+str(i),uaIP=pjListenAddress,regExpiresTimeout=300))
		#print('Len =' + str(len(tcUAcli)) )

	if tcMasterUA.uaAccountInfo.reg_status != 200:
		print(Fore.RED + 'Master UA failed to register!')
		logging.error('Master UA failed to register!')
		print(str(tcMasterUA.uaAccountInfo.uri) + ' state: ' + str(tcMasterUA.uaAccountInfo.reg_status) + ' - ' + str(tcMasterUA.uaAccountInfo.reg_reason))
		return False
	else:
		print(Fore.GREEN + 'Master UA Registered')
		logging.info('Master UA Registered')

	if tcSecondaryMasterUA.uaAccountInfo.reg_status != 200:
		print(Fore.RED + 'Secondary Master UA failed to register!')
		logging.error('Secondary Master UA failed to register!')
		print(str(tcMasterUA.uaAccountInfo.uri) + ' state: ' + str(tcMasterUA.uaAccountInfo.reg_status) + ' - ' + str(tcMasterUA.uaAccountInfo.reg_reason))
		return False
	else:
		print(Fore.GREEN + 'Secondary Master UA Registered')
		logging.info('Secondary Master UA Registered')

	if extUAcli.uaAccountInfo.reg_status != 200:
		print(Fore.RED + 'Client UA failed to register!')
		logging.error('Client UA failed to register!')
		print(str(tcMasterUA.uaAccountInfo.uri) + ' state: ' + str(tcMasterUA.uaAccountInfo.reg_status) + ' - ' + str(tcMasterUA.uaAccountInfo.reg_reason))
		return False
	else:
		print(Fore.GREEN + 'External UA Registered')
		logging.info('External UA Registered')

	allCliRegistered = False
	cnt = 0
	while not allCliRegistered:
		if cnt > 50:		
			print(Fore.RED + 'Some client UAs failed to register!')

			for i in range(tcUACCount):
				print(str(tcUAcli[i].uaAccountInfo.uri) + ' state: ' + str(tcUAcli[i].uaAccountInfo.reg_status) + ' - ' + str(tcUAcli[i].uaAccountInfo.reg_reason))
				logging.warning(str(tcUAcli[i].uaAccountInfo.uri) + ' state: ' + str(tcUAcli[i].uaAccountInfo.reg_status) + ' - ' + str(tcUAcli[i].uaAccountInfo.reg_reason))
			logging.error('Some client UAs failed to register!')
			return False
		cnt += 1
		time.sleep(0.1)
		for i in range(tcUACCount):
			print('.', end='')
			if tcUAcli[i].uaAccountInfo.reg_status != 200:
				allCliRegistered = False
				break
			else:
				allCliRegistered = True
	print('\n')
	print(Fore.GREEN + 'All UAC registered...')
	logging.info('All UAC registered')

	ccn.subscriberSipInfo(dom=testingDomain,sipNumber=masterNumber,sipGroup=SIPgroup,complete=False)

	time.sleep(1)

	return True

def basicTest():
	logging.info('Basic Teleconference test')
	Failure = False

	if tcStartConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,templateName=testTemplateName):
		print(Fore.GREEN +'Start teleconference success')
		logging.info('Start teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference starting...')
		logging.error('Smthing happen wrong with teleconference starting...')
		hangupAll()
		return False

	time.sleep(5)

	if tcMasterUA.uaCurrentCallInfo.state != 5:
		print(Fore.RED + 'Master UA is in wrong state')
		logging.error('Master UA is in wrong state')
		hangupAll()
		return False
	else:
		print(Fore.GREEN + 'Master UA is in active call state')
		logging.info('Master UA is in active call state')

	print(Style.BRIGHT + 'Connecting user one by one')
	logging.info('Connecting user one by one')
	firstUACliNum = int(config.testConfigJson['UsersClients'][0]['Number'])
	for num in range(firstUACliNum, firstUACliNum + tcUACCount):
		if tcExpPushOnUser(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,memberNumber=str(num)):
			print(Fore.GREEN +'User '+ str(num) +' command sent')
		else:
			print(Fore.RED + 'Smthing happen wrong with sending user '+ str(num) +' command sent...')

	print(Style.BRIGHT + 'Teleconference in progress.... ')
	logging.info('Teleconference in progress.... ')
	cnt=0 # timer
	confDuration = 10 + (tcUACCount * 2)

	while cnt < confDuration:		
		time.sleep(1)
		print('.',end='')
		cnt += 1

	Failure = False
	for i in range(tcUACCount):
		if tcUAcli[i].uaCurrentCallInfo.state != 5:
			print(Fore.YELLOW +'UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			logging.warning('UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			Failure = True

	if Failure:
		print('Some subscribers were in wrong call state')
		logging.error('Some subscribers were in wrong call state')
		hangupAll()
		return False

	print(Style.BRIGHT + 'Releasing use by it self')
	logging.info('Releasing use by it self')
	for i in range(tcUACCount):
		try:
			tcUAcli[i].uaCurrentCall.hangup(code=200, reason='Release')
		except:
			pass
	print('Sleep 10 sec')
	time.sleep(10)


	if tcMasterUA.uaCurrentCallInfo.state != 5:
		print(Fore.YELLOW +'Master UA in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		logging.warning('Master UA in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
	else:
		print(Fore.GREEN + 'Master UA still in conference - it is ok. Continue...')
		logging.info('Master UA still in conference - it is ok. Continue...')

	print('Making group call...')
	logging.info('Making group call...')
	if tcGroupAll(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Group call command sent')
	else:
		print(Fore.RED + 'Smthing happen wrong with sending a group call command...')
		hangupAll()
		return False

	print(Style.BRIGHT + 'Teleconference in progress.... ')
	logging.info('Teleconference in progress.... ')

	cnt=0 # timer
	confDuration = 10 + (tcUACCount * 2)

	while cnt < confDuration:
		failureFlag = False
		time.sleep(1)
		print('.',end='')
		cnt += 1

	Failure = False
	for i in range(tcUACCount):
		if tcUAcli[i].uaCurrentCallInfo.state != 5:
			print(Fore.YELLOW +'UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			logging.warning('UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			Failure = True

	if Failure:
		print('Some subscribers were in wrong call state')
		logging.error('Some subscribers were in wrong call state')
		hangupAll()
		return False

	print(Style.BRIGHT + 'Stoping teleconference....')
	logging.info('Stoping teleconference....')
	if tcStopConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Stop teleconference success')
		logging.info('Stop teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference stoping...')
		logging.error('Smthing happen wrong with teleconference stoping...')
		hangupAll()
		return False

	time.sleep(5)

	UAnotReleased = False
	if tcMasterUA.uaCurrentCallInfo.state != 6:
		print(Fore.YELLOW +'Master UA in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		logging.warning('Master UA in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
	else:
		print(Fore.GREEN + 'Master UA successfully released')
		logging.info('Master UA successfully released')

	for i in range(tcUACCount):
		if tcUAcli[i].uaCurrentCallInfo.state != 6:
			print(Fore.YELLOW +'UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			logging.warning('UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			UAnotReleased = True

	if UAnotReleased:
		print(Fore.RED + 'Some UAs didnt disconected')
		logging.error('Some UAs didnt disconected')
		hangupAll()
		return False
	else:
		print(Fore.GREEN +'All UA successfully released')
		logging.info('All UA successfully released')
		return True

def riseForVoice():
	global recievedPOSTstr
	logging.info('Ask for voice test')

	if tcStartConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,templateName=testTemplateName):
		print(Fore.GREEN +'Start teleconference success')
		logging.info('Start teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference starting...')
		logging.error('Smthing happen wrong with teleconference starting...')
		hangupAll()
		return False

	time.sleep(2)

	if tcMasterUA.uaCurrentCallInfo.state != 5:
		print(Fore.RED + 'Master UA is in wrong state')
		logging.error('Master UA is in wrong state')
		hangupAll()
		return False
	else:
		print(Fore.GREEN + 'Master UA is in active call state')
		logging.info('Master UA is in active call state')

	print('Making group call...')
	logging.info('Making group call...')
	if tcGroupAll(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Group call command sent')
	else:
		print(Fore.RED + 'Smthing happen wrong with sending a group call command...')
		logging.error('Smthing happen wrong with sending a group call command...')
		hangupAll()
		return False

	time.sleep(1)

	for i in range(tcUACCount):
		if tcUAcli[i].uaCurrentCallInfo.state != 5:
			print(Fore.YELLOW +'UA '+ str(i) + ' in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			logging.warning('UA '+ str(i) + ' in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)

	print(Style.BRIGHT + 'Teleconference in progress.... ')
	logging.info('Teleconference in progress.... ')

	cnt=0 # timer
	confDuration = 10 + (tcUACCount * 2)

	voiceOnNotifyRecieved = False
	voiceOnBlinkLedRecieved = False
	while cnt < confDuration:		
		time.sleep(1)
		print('.',end='')
		cnt += 1
		if cnt == 6:
			print(Style.BRIGHT +'Sending DTMF...')
			logging.info('Sending DTMF...')
			tcUAcli[0].sendInbandDTMF(dtmfDigit='1')
		if cnt > 6:
			if '<Text>Дайте мне голос, пожалуйста</Text>' in  recievedPOSTstr:
				voiceOnNotifyRecieved = True
				logging.info('Recieved Yealink Info screen message')
			if 'Led: EXP-1-1-GREEN=fastflash' in recievedPOSTstr:
				voiceOnBlinkLedRecieved = True
				logging.info('Recieved Yealink exp. panel LED fastflash')

	Failure = False
	for i in range(tcUACCount):
		if tcUAcli[i].uaCurrentCallInfo.state != 5:
			print(Fore.YELLOW +'UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			logging.warning('UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			Failure = True
	if Failure:
		print('Some subscribers were in wrong call state')
		logging.error('Some subscribers were in wrong call state')
		hangupAll()
		return False

	print(Style.BRIGHT + 'Stoping teleconference....')
	logging.info('Stoping teleconference....')
	'''
	if tcStopConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Stop teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference stoping...')
		return False
		#sys.exit(1)	
	'''
	try:
		logging.info('Hanging up master')
		tcMasterUA.uaCurrentCall.hangup(code=200, reason='Conference finish!')
	except:
		pass

	time.sleep(3)

	UAnotReleased = False
	if tcMasterUA.uaCurrentCallInfo.state != 6:
		print('Master UA in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		logging.warning('Master UA in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		return False
	else:
		print(Fore.GREEN + 'Master UA successfully released')
		logging.info('Master UA successfully released')

	Failure = False
	for i in range(tcUACCount):
		if tcUAcli[i].uaCurrentCallInfo.state != 6:
			print('UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			logging.warning('UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
			Failure = True

	if not voiceOnNotifyRecieved:
		print(Fore.RED + 'Didnt recieved Notify message ')
		logging.error('Didnt recieved Notify message ')
		hangupAll()
		return False
	else:
		print(Fore.GREEN + 'Voice on notify message successful recieved')
		logging.info('Voice on notify message successful recieved')

	if not voiceOnBlinkLedRecieved:
		print(Fore.RED + 'LED indicator didnt blinked on voice notification')
		logging.error('LED indicator didnt blinked on voice notification')
		hangupAll()
		return False
	else:
		print(Fore.GREEN + 'LED indicator successful changed on voice notification')
		logging.info('LED indicator successful changed on voice notification')

	if Failure:
		print('Some subscribers were in wrong call state')
		logging.error('Some subscribers were in wrong call state')
		hangupAll()
		return False
	else:
		print(Fore.GREEN + 'All UA successfully released')
		logging.info('All UA successfully released')
		return True
	'''
	if UAnotReleased:
		print(Fore.RED + 'Some UAs didnt disconected')
		hangupAll()
		return False
	else:
		print(Fore.GREEN +'All UA successfully released')		
	return True
	'''

def connectToConfViaTransfer():
	logging.info('Making conference with external client')
	Failure = True

	if tcStartConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,templateName=testTemplateName):
		print(Fore.GREEN +'Start teleconference success')
		logging.info('Start teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference starting...')
		logging.error('Smthing happen wrong with teleconference starting...')
		hangupAll()
		return False

	time.sleep(3)

	if tcMasterUA.uaCurrentCallInfo.state != 5:
		print(Fore.RED + 'Master UA is in wrong state')
		logging.warning('Master UA is in wrong state')
		hangupAll()
		return False
	else:
		print(Fore.GREEN + 'Master UA is in active call state')
		logging.info('Master UA is in active call state')

	logging.info('Holding')
	tcMasterUA.uaCurrentCall.hold()
	time.sleep(1)

	logging.info('Making call to external user from secondary master accaunt')
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
		logging.error('Call not recieved')
		hangupAll()
		return False
	else:
		print('Call answered')
		logging.info('Call answered')

	time.sleep(2)
	print('transfering to conference...')
	logging.info('transfering to conference...')

	tcSecondaryMasterUA.ctr_request(dstURI=masterNumber+'@'+testingDomain,currentCall=tcSecondaryMasterUA.uaCurrentCall)
	time.sleep(1)
	print('hanging up...')
	try:
		tcSecondaryMasterUA.uaCurrentCall.hangup(code=200, reason='Release after transfer')
	except:
		pass

	logging.info('Check if secondry master released')
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
		logging.error('Secondary Master call not released')
		hangupAll()
		return False
	else:
		print(Fore.GREEN +'Secondary Master released after transfer')
		logging.info('Secondary Master released after transfer')

	time.sleep(1)

	#tcSecondaryMasterUA
	print('Unholding master...')
	logging.info('Unholding master...')
	tcMasterUA.uaCurrentCall.unhold()

	cnt=0 # timer
	confDuration = 10 


	Failure = False
	while cnt < confDuration:	
		failureFlag = False	
		time.sleep(1)
		print('.',end='')
		cnt += 1
		if extUAcli.uaCurrentCallInfo.state != 5:
			print(Fore.YELLOW +'Client external UA still in wrong state: ' + str(extUAcli.uaAccountInfo.uri) + ' ' + extUAcli.uaCurrentCallInfo.state_text)
			logging.warning('Client external UA still in wrong state: ' + str(extUAcli.uaAccountInfo.uri) + ' ' + extUAcli.uaCurrentCallInfo.state_text)
			Failure = True
		if tcMasterUA.uaCurrentCallInfo.state != 5:
			print(Fore.YELLOW +'Master UA still in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
			logging.warning('Master UA still in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
			Failure = True

	if Failure:
		print('Some subscribers were in wrong call state')
		logging.error('Some subscribers were in wrong call state')
		hangupAll()
		return False

	print('Stoping teleconference....')
	logging.info('Stoping teleconference....')
	if tcStopConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Stop teleconference success')
		logging.info('Stop teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference stoping...')
		logging.error('Smthing happen wrong with teleconference stoping...')
		hangupAll()
		return False

	time.sleep(5)

	UAnotReleased = False
	if extUAcli.uaCurrentCallInfo.state != 6:
		print(Fore.YELLOW +'Client external UA still in wrong state: ' + str(extUAcli.uaAccountInfo.uri) + ' ' + extUAcli.uaCurrentCallInfo.state_text)
		logging.warning('Client external UA still in wrong state: ' + str(extUAcli.uaAccountInfo.uri) + ' ' + extUAcli.uaCurrentCallInfo.state_text)
		UAnotReleased = True
	else:
		print(Fore.GREEN +'Client UA Released')
		logging.info('Client UA Released')

	if tcMasterUA.uaCurrentCallInfo.state != 6:
		print(Fore.YELLOW +'Master UA still in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		logging.warning('Master UA still in wrong state: ' + str(tcMasterUA.uaAccountInfo.uri) + ' ' + tcMasterUA.uaCurrentCallInfo.state_text)
		UAnotReleased = True
	else:
		print(Fore.GREEN +'Master UA Released')
		logging.info('Master UA Released')

	if UAnotReleased:
		print(Fore.RED + 'Some UAs didnt disconected')
		logging.error('Some UAs didnt disconected')
		hangupAll()
		return False
	else:
		print(Fore.GREEN +'All UA successfully released')
		logging.info('All UA successfully released')
		return True
	
def domainActiveChannelsLimit():
	logging.info('Test active channels limits')
	print('Reconfiguring tc_count_active_channels property:')
	logging.info('Reconfiguring tc_count_active_channels property:')

	tcActiveChanLimit = 2

	returnedFromSSH = ccn.executeOnSSH('domain/'+testingDomain+'/properties/restrictions/set tc_count_active_channels ' + str(tcActiveChanLimit))
	print(returnedFromSSH)
	if ('changed' in returnedFromSSH) or ('set to' in returnedFromSSH):
		print(Fore.GREEN +'Property changed')
		logging.info('Property changed')
	else:
		print(Fore.RED + 'Failed to change property tc_count_active_channels')
		logging.error('Failed to change property tc_count_active_channels')
		hangupAll()
		return False

	time.sleep(1)

	if tcStartConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,templateName=testTemplateName):
		print(Fore.GREEN +'Start teleconference success')
		logging.info('Start teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference starting...')
		logging.error('Smthing happen wrong with teleconference starting...')
		hangupAll()
		return False

	time.sleep(3)

	if tcMasterUA.uaCurrentCallInfo.state != 5:
		print(Fore.RED + 'Master UA is in wrong state')
		logging.error('Master UA is in wrong state')
		hangupAll()
		return False
	else:
		print(Fore.GREEN + 'Master UA is in active call state')
		logging.info('Master UA is in active call state')

	print(Style.BRIGHT + 'Connecting user one by one')
	logging.info('Connecting user one by one')

	firstUACliNum = int(config.testConfigJson['UsersClients'][0]['Number'])
	for num in range(firstUACliNum, firstUACliNum + tcUACCount):
		if tcExpPushOnUser(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber,memberNumber=str(num)):
			print(Fore.GREEN +'User '+ str(num) +' command sent')
			logging.info('User '+ str(num) +' command sent')
		else:
			print(Fore.RED + 'Smthing happen wrong with sending user '+ str(num) +' command sent...')
			logging.warning('Smthing happen wrong with sending user '+ str(num) +' command sent...')
		time.sleep(0.5)

	print(Style.BRIGHT + 'Teleconference in progress.... ')
	logging.info('Teleconference in progress.... ')
	cnt=0 # timer
	confDuration = 10 + (tcUACCount * 2)

	Failure = False
	failureFlag = False
	while cnt < confDuration:
		time.sleep(1)
		print('.',end='')
		cnt += 1
		for i in range(0,tcActiveChanLimit):
			Failure = False
			if tcUAcli[i].uaCurrentCallInfo.state != 5:
				print(Fore.YELLOW +'UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
				logging.warning('UA '+ str(i) + ' still in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
				Failure = True
		if Failure:
			failureFlag = True

		Failure = False
		for i in range(tcActiveChanLimit,tcUACCount):
			if tcUAcli[i].uaCurrentCallInfo.state == 5:
				print(Fore.YELLOW +'UA '+ str(i) + ' in wrong state: ' + str(tcUAcli[i].uaAccountInfo.uri) + ' ' + tcUAcli[i].uaCurrentCallInfo.state_text)
				Failure = True
		if Failure:
			failureFlag = True


	if failureFlag:
		print('Some subscribers were in wrong call state')
		logging.error('Some subscribers were in wrong call state')
		hangupAll()
		return False

	print(Style.BRIGHT + 'Stoping teleconference....')
	if tcStopConf(dom=testingDomain,restHost=restHost,restPort=restPort,masterNumber=masterNumber):
		print(Fore.GREEN +'Stop teleconference success')
		logging.info('Stop teleconference success')
	else:
		print(Fore.RED + 'Smthing happen wrong with teleconference stoping...')
		logging.error('Smthing happen wrong with teleconference stoping...')
		hangupAll()
		return False

	time.sleep(5)

	print('Cleaning property tc_count_active_channels')
	logging.info('Cleaning property tc_count_active_channels')
	returnedFromSSH = ccn.executeOnSSH('domain/'+testingDomain+'/properties/restrictions/clean tc_count_active_channels')
	print(returnedFromSSH)
	if 'unseted' in returnedFromSSH:
		print(Fore.GREEN +'Property changed')
		logging.info('Property changed')
	else:
		print(Fore.RED + 'Failed to change property tc_count_active_channels')
		logging.info('Failed to change property tc_count_active_channels')
		hangupAll()
		return False
	return not Failure

def hangupAll(reason='All calls finish due to failure'):
	print('Hangup all calls : ' + reason)
	logging.info('Hangup all calls : ' + reason)
	for pjSubscriber in tcUAcli:
		try:
			pjSubscriber.uaCurrentCall.hangup(code=200, reason=reason)
		except Exception as e:
			pass
	try:
		tcMasterUA.uaCurrentCall.hangup(code=200, reason=reason)
	except Exception as e:
		pass

	try:
		tcSecondaryMasterUA.uaCurrentCall.hangup(code=200, reason=reason)
	except Exception as e:
		pass

	try:
		tcExtMember.uaCurrentCall.hangup(code=200, reason=reason)
	except Exception as e:
		pass


def iterTest(testMethod, testName, terminateOnFailure = False):
	if testMethod:
		res = True
		resultStr = testName + ' - OK'
		logging.info(resultStr)
	else:
		res = False
		resultStr = testName + ' - FAILED'
		logging.error(resultStr)
		if terminateOnFailure:
			sys.exit(1)
	testResultsList.append(resultStr)
	print(resultStr)
	return res

#############################################################################################

success = True

# Start Yealink http server
httpYealinkListen_T = Thread(target=runHTTPYealinkListener, name='httpYealinkListen', daemon=True)
httpYealinkListen_T.start()

testResultsList.append(' ------TEST RESULTS------- ')
#iterTest(preconfigure(),'Preconfiguration',True)
success = success&iterTest(registerUAs(),'SIP register',True)
success = success&iterTest(basicTest(),'Basic Teleconference')
#success = success&iterTest(riseForVoice(),'Request for voice')
#success = success&iterTest(connectToConfViaTransfer(),'Connect to conference external user')
#success = success&iterTest(domainActiveChannelsLimit(),'License active users limit')
#success = success&iterTest(basicTest(),'One more repeat of Basic Teleconference')

print(Style.BRIGHT + 'Total Results of Teleconference tests:')
for reportStr in testResultsList:
	print(reportStr)
	logging.info(reportStr)

if not success:
	print(Fore.RED +'Some tests failed!')
	logging.error('Some tests failed!')
	sys.exit(1)
else:
	print(Fore.GREEN +'It seems to be all FINE...')
	logging.info('All test OK!')
	print('We did it!!')
	sys.exit(0)