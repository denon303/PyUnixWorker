#==============================================================================
#title           :PyUnixWorker.py
#description     :Aplicacion consola para realizar tareas masivas mediante ssh en maquinas Unix/Linux.
#author          :Daniel Bejar Diaz
#date            :31/01/2019
#version         :0.1
#usage           :python PyUnixWorker.py
#notes           :
#python_version  :3.7.1  
#==============================================================================

import paramiko, time, os, sys
from paramiko_expect import SSHClientInteraction
from random import shuffle
import openpyxl

# PARAMIKO & NETVARS
global client
global remote_conn
global jumpNodesIndex
global state

# LOGIN VARIABLES
tUser = "t878xxx"
tPass = "xxxxxxxxx"
passwdPrompts = ["password:", "Password:", "password: ", "Password: " "password: ' ", "Password ' "]

# JUMPNODES DICTIONARIES...
jump01 =  {  "hostname": "jump01", "ip": "10.0.0.1", "login" : "root" , "pass" : "madrid01", "jump": None, "strictoption" : 1, "Description" : "Salto Alternativa" } # Alternativa
#jump02 =   {  "hostname": "jump02",  "ip": "10.0.0.1" , "login" : tUser, "pass" : tPass, "jump": jump01, "Description" : "Salto Empresas" } #Salto Empresas
jump03   =  {  "hostname": "jump03", "ip": "10.0.0.1", "login" : tUser , "pass" : tPass, "jump": None, "Description" : "Salto RIMA" } # Salto RIMA
jump04 =  {  "hostname": "jump04", "ip": "10.0.0.1", "login" : tUser , "pass" : tPass, "jump": None, "Description" : "Salto NIMBA" } # Salto RIMA
jump05 =  {  "hostname": "jump05", "ip": "10.0.0.1", "login" : tUser , "pass" : tPass, "jump": None, "Description" : "Salto NIMBA" } # Salto NIMBA
#jump06 =  {  "hostname": "jump06", "ip": "10.0.0.1", "login" : tUser , "pass" : tPass, "jump": jump02, "Description" : "Salto Moviles" } # Salto Moviles 
#jump07 =  {  "hostname": "jump07", "ip": "10.0.0.1", "login" : tUser , "pass" : tPass, "jump": jump02, "Description" : "Salto Moviles" } # Salto Moviles 

jumpNodes = [ jump01, jump03, jump04, jump05 ]

# TARGET SERVERS VARIABLES
targetServer = None

# EXCEL VARIABLES
inputExcl = openpyxl.load_workbook('C:/PETICION QUITAR EXPIRACION.xlsx') 
inputSheet= inputExcl["Hoja1"]
#inputSheet= inputExcl.get_sheet_by_name(name = 'Hoja1')
inventExcl = openpyxl.load_workbook('C:/InventarioUnix.xlsx', read_only = True, data_only = True)
inventSheet= inventExcl["t_inventario"]
#inventSheet= inventExcl.get_sheet_by_name(name = 't_inventario')

class DevNull:
    def write(self, msg):
        pass

def StartWork():
    workcounter = 1
    for row in inputSheet.iter_rows(min_row=150, max_row=inputSheet.max_row, min_col=1, max_col=1, values_only=True):
        for cell in row:
            SearchInventory(workcounter, cell)
            time.sleep(5)
            workcounter += 1
            
def SearchInventory(number, hostname):
    print("\n *********************************************************************************************\n ")
    print(" *** Tarea:" + str(number) + " Hostname: " + hostname)
    print(" *** Buscando datos en el inventario para " + hostname + " ...")

    for row in inventSheet.iter_rows(min_row=1, max_row=inventSheet.max_row, min_col=1, max_col=1, values_only=False):
        for cell in row: 
            if str(hostname) == cell.value:
                targetServer = { "hostname": hostname, "ip": inventSheet.cell(row=cell.row, column=13).value, "pass": inventSheet.cell(row=cell.row, column=14).value }
                #print (targetServer)
                JumpNodeSearch(targetServer)
                break

def JumpNodeSearch(targetServer):
    global jumpNodesIndex
    global state
    state = "SEARCHJUMPNODE"
    print ("\n     Buscando Nodo de salto, puede tardar varios minutos...\n")
    tryJumpNode = 1
    for jumpNode in jumpNodes:
        if state == "NO-RESPONSE-FROM-JUMPNODE":
            print("Cambia el estado a: NO-RESPONSE-FROM-JUMPNODE")
            break
        elif state == "LOGIN-USER-OK":
            break
        elif state == "LOGIN-PASSWD-FAIL":
            break
        elif state == "TARGET-REACHED-FROM-JUMPNODE":
            print("Cambia el estado a: TARGET-REACHED-FROM-JUMPNODE")
            break
#        if state == "CONNECT-FAIL-JUMPNODE":
#            continue
        else:
            if jumpNode["jump"] == None:
                ConnectToJumpNode(jumpNode, targetServer, tUser, tPass, tryJumpNode) #, 10, 20)
            else:
                pass
                #ConnectToJumpNode(jumpNode, targetServer, tUser, targetServer["pass"], tryJumpNode) #, 10, 20)
        time.sleep(4)
        tryJumpNode += 1
    print("# Esta tarea a terminado en este servidor con estado: " + state)
               
def GetOutputSSH(bufferSize, sleepTime):
    time.sleep(sleepTime)
    output = remote_conn.recv(bufferSize)
    outputSplitLines = str(output).split("\\r\\n")  
    return outputSplitLines

def SendString(commandString, jumpNode, targetServer, hidePass):
    if hidePass:
        print ("     Enviando contraseña: " + "********"  + " desde: " + jumpNode["hostname"] + " hacia: " + targetServer["hostname"])
    else:
        print ("     Ejecutando: " + commandString + " desde: " + jumpNode["hostname"] + " hacia: " + targetServer["hostname"])
    remote_conn.send(commandString  + '\n')

def ConnectToJumpNode(jumpNode, targetServer, user, passwd, tryJumpNode): #, retry_interval, retry_timeout):
    global state
    global client
    global remote_conn
    
##    retry_interval = float(retry_interval)
##    retry_timeout = int(retry_timeout)
##    timeout_start = time.time()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
##    while time.time() < timeout_start + retry_timeout:
##        time.sleep(retry_interval)  

    state = "CONNECT-TRY-JUMPNODE"

    try:
        print ("     " + str(tryJumpNode) + ") - Intentando autenticar con tUSER desde: " + jumpNode["hostname"] + " " + str(jumpNode["ip"]) + " hacia: " + str(targetServer["hostname"] + " " + str(targetServer["ip"])))
           
        client.connect(jumpNode["ip"], username=jumpNode["login"], password=jumpNode["pass"], timeout=10) # banner_timeout=60
        remote_conn = client.invoke_shell()
        
        state = "CONNECTED-TO-JUMPNODE"

        if jumpNode["strictoption"] == 1:
            SendString('ssh -o StrictHostKeyChecking=no ' + user + '@' + str(targetServer["ip"]), jumpNode, targetServer, False)
        if jumpNode["strictoption"] == 2:
            SendString('ssh ' + user + '@' + str(targetServer["ip"]), jumpNode, targetServer, False)
        
        if user != "root":
            pass
            LoginToServerWithTUSER(GetOutputSSH(1000,6), jumpNode, targetServer, user, passwd)
        else:
            pass
            #LoginToGetOutputSSH(1000,6), jumpNode, targetServer, user, passwd)
	    
    except paramiko.ssh_exception.AuthenticationException as e:
        print("### EXCEPTION Code(1)...")
        state = "CONNECT-FAIL-JUMPNODE"
    except paramiko.ssh_exception.BadHostKeyException as e:
        print("### EXCEPTION Code(2)...")
        state = "CONNECT-FAIL-JUMPNODE"
    except paramiko.ssh_exception.ChannelException as e:
        print("### EXCEPTION Code(3)...")
        state = "CONNECT-FAIL-JUMPNODE"
    except paramiko.ssh_exception.NoValidConnectionsError as e:
        print('SSH transport is not ready...')
        state = "CONNECT-FAIL-JUMPNODE"
    except paramiko.ssh_exception.PartialAuthentication as e:
        print("### EXCEPTION Code(5)...")
        state = "CONNECT-FAIL-JUMPNODE"
    except paramiko.ssh_exception.PasswordRequiredException as e:
        print("### EXCEPTION Code(6)...")
        state = "CONNECT-FAIL-JUMPNODE"
    except paramiko.ssh_exception.ProxyCommandFailure as e:
        print("### EXCEPTION Code(7)...")
        state = "CONNECT-FAIL-JUMPNODE"
    except paramiko.ssh_exception.SSHException as e:
        print('SSH transport is available!')
        state = "CONNECT-FAIL-JUMPNODE"
    except:
        print("### GENERAL EXCEPTION Code(8)...")
        state = "CONNECT-FAIL-JUMPNODE"
    finally:
        if client:
            client.close()

def LoginToServerWithTUSER(outputSplitLines, jumpNode, targetServer, user, passwd):
    state = "LOGIN-USER-PASSWD-PROMPT"
    print(str(outputSplitLines[len(outputSplitLines)-1]))
    tempWords = str(outputSplitLines[len(outputSplitLines)-1].Split(" "))
    print(tempWords)
    
    #if any(w in passwdPrompts for w in tempWords):
    for w in passwdPrompts:
        if w in tempWords:
            match = True
    
    if match == True:
        state = "TARGET-REACHED-FROM-JUMPNODE"
        #AuthTUSER(jumpNode, targetServer, user, passwd)
        print (state + " ############################################################################")
        return 0
    else:
        state = "NO-RESPONSE-FROM-JUMPNODE"
        return 1
           
def AuthTUSER(jumpNode, targetServer, user, passwd):
    state = "LOGIN-USER-PASSWD-SEND"
    SendString(passwd, jumpNode, targetServer, False) #targetServer["pass"]
    time.sleep(5)
    output = remote_conn.recv(5000)
    print(str(output))
    if str(output).find("DISPLAY=(") > 0:
       state = "LOGIN-USER-LOGPROMPT"
       SendString("\n\n", targetServer, False)
       time.sleep(2)
       output = remote_conn.recv(5000)
       if str(output).find("$") > 0: 
           print("     OK [TUSER] - Conectado como: " + user)
           state = "LOGIN-USER-OK"
           #MakeWork()
       else:
           print("     NOK [TUSER] - Cambiando estado a: " + state)
           state = "LOGIN-PASSWD-FAIL"
           return 1
    else:
        if str(output).find("$") > 0: 
            print("     OK [TUSER] - Conectado como: " + user)
            state = "LOGIN-USER-OK"
            #MakeWork()
        else:
            print("     NOK [TUSER] - Cambiando estado a: " + state)
            state = "LOGIN-PASSWD-FAIL"
            return 1


sys.stderr = DevNull()   
StartWork()
