import time
import math
from pymavlink import mavutil

# master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
# master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
# master = mavutil.mavlink_connection('udpin:localhost:14550')
master = mavutil.mavlink_connection('tcp:127.0.0.1:5762')

master.wait_heartbeat()
print("Połączono z systemem. ID:", master.target_system)

def setGuidedMode():
    modeId = master.mode_mapping()['GUIDED']
    master.set_mode(modeId)
    time.sleep(1)

def armAndTakeoff(target_altitude):
    print("Uzbrajanie silników trwa...")
    master.arducopter_arm()

    master.motors_armed_wait()
    print("Uzbrajanie silników się powiodło")

    print("Startowanie na wysokość ", target_altitude, "...", sep="")

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, 0, 0, 0,
        target_altitude
    )

    time.sleep(10)
    print("Osiągnięto wysokość startową")

def goToLocation(lat, lon, alt):
    print(f"Przelot do punktu GPS: {lat}, {lon} na wysokosć {alt}")

    master.mav.mission_item_int_send(
        master.target_system,
        master.target_component,
        0,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        2,
        0, 0, 0, 0, 0,
        int(lat * 1e7),
        int(lon * 1e7),
        alt
    )

def simulatedSensorCheck():
    print("Osiągnięto obszar badań. Sprawdzanie czujników...")
    time.sleep(2) #normalnie tutaj by odpalał się jakiś czujnik, kamera czy LiDAR
    objectDetected = True

    if objectDetected:
        print("Sukces - wykryto obiekt!")
        return True
    else:
        print("Nie wykryto obiektu")
        return False

def returnToLaunch():
    print("Rozpoczynanie powrotu do punktu startowego (RTL)...")
    modeId = master.mode_mapping()['RTL']
    master.set_mode(modeId)
    time.sleep(2)

    while True:
        msg = master.recv_match(type='HEARTBEAT', blocking=True, timeout=1)

        if not master.motors_armed():
            print('Lądowanie zakończone sukcesem!')
            break
        else:
            print('Powrót do bazy trwa...')


def changeSpeed(speedMps):
    print(f"Zmienianie prędkości na {speedMps}m/s...")
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED,
        0,
        1, #typ prędkości - przelotowa
        speedMps,
        -1,
        0, 0, 0, 0
    )

def waitUntilReachedTarget(targetLat, targetLon, tresholdMeters=3):
    print("Oczekiwanie na dotarcie do celu...")
    speedReduced = False

    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_POSITION,
        4, #4 na sekunde
        1
    )

    while True:
        msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=0.5)

        if msg:
            currentLat = msg.lat / 1e7
            currentLon = msg.lon / 1e7

            latDiff = abs(currentLat - targetLat) * 111000
            lonDiff = abs(currentLon - targetLon) * 111000 * math.cos(math.radians(targetLat))

            distance = math.sqrt(latDiff**2 + lonDiff**2)
            print(f"Aktualna odległość do celu: {distance:.2f}m")

            if distance < 15 and not speedReduced:
                print("Zbliżanie się do celu, Redukcja prędkości...")
                changeSpeed(2.5)
                speedReduced = True


            if distance < tresholdMeters:
                print("Cel osiągnięty!")
                break


if __name__ == "__main__":
    setGuidedMode()
    armAndTakeoff(10)

    targetLat = -35.362800
    targetLon = 149.165200

    goToLocation(targetLat, targetLon, 10)

    waitUntilReachedTarget(targetLat, targetLon, 3)

    if simulatedSensorCheck():
        print("Reakcja systemu: Zawis nad obiektem na 5s...")
        time.sleep(5)

    returnToLaunch()

