#!/usr/bin/python3 -u

import sys, fcntl, time

def decrypt(key,  data):
	cstate = [0x48,  0x74,  0x65,  0x6D,  0x70,  0x39,  0x39,  0x65]
	shuffle = [2, 4, 0, 7, 1, 6, 5, 3]
	
	phase1 = [0] * 8
	for i, o in enumerate(shuffle):
		phase1[o] = data[i]
	
	phase2 = [0] * 8
	for i in range(8):
		phase2[i] = phase1[i] ^ key[i]
	
	phase3 = [0] * 8
	for i in range(8):
		phase3[i] = ( (phase2[i] >> 3) | (phase2[ (i-1+8)%8 ] << 5) ) & 0xff
	
	ctmp = [0] * 8
	for i in range(8):
		ctmp[i] = ( (cstate[i] >> 4) | (cstate[i]<<4) ) & 0xff
	
	out = [0] * 8
	for i in range(8):
		out[i] = (0x100 + phase3[i] - ctmp[i]) & 0xff
	
	return out

def hd(d):
	return " ".join("%02X" % e for e in d)


def get_co2(values):
    if 0x50 in values:
        return values[0x50]
    return None


def get_all(device):
    key = [0xc4, 0xc6, 0xc0, 0x92, 0x40, 0x23, 0xdc, 0x96]
    HIDIOCSFEATURE_9 = 0xC0094806
    set_report = bytearray([0x00] + key)

    with open(device, "a+b", 0) as fp:
        fcntl.ioctl(fp, HIDIOCSFEATURE_9, set_report)

        co2 = None
        temperature = None
        while co2 is None or temperature is None:
            data = list(fp.read(8))
            decrypted = None

            if data[4] == 0x0d and (sum(data[:3]) & 0xff) == data[3]:
                decrypted = data
            else:
                decrypted = decrypt(key, data)

            if decrypted[4] != 0x0d or (sum(decrypted[:3]) & 0xff) != decrypted[3]:
                print("Checksum error")
            else:
                op = decrypted[0]
                val = decrypted[1] << 8 | decrypted[2]

                if op == 0x50:  # CO2 Value
                    co2 = val
                elif op == 0x42:  # Temperature Value
                    temperature = val / 16.0 - 273.15
                if co2 is None or temperature is None:
                    time.sleep(0.1)  # Sleep for 100 milliseconds
        return {'CO2': co2, 'Temperature': temperature}


if __name__ == "__main__":
    device = '/dev/hidraw0'  # Default device
    if len(sys.argv) > 1:
        device = sys.argv[1]

    result = get_all(device)
    print(result)
