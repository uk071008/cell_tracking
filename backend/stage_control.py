import socket
import time

class MicosStageController:
    def __init__(self, ip ="141.51.197.172", port=23):
        self.ip = ip
        self.port = port
        self.sock = None
        self.connected = False

        self.soft_limit_x_min = None
        self.soft_limit_x_max = None
        self.soft_limit_y_min = None
        self.soft_limit_y_max = None
        self.soft_limit_z_min = None
        self.soft_limit_z_max = None

    def set_current_as_zero(self):
            """Redefines current position as 0,0,0 and shifts soft limits to match."""
            if not self.connected:
                return False

            # 1. Ask the stage where it is BEFORE we reset it
            current_pos = self.query_position()
            if not current_pos:
                print("Error: Could not read position to calculate offset.")
                return False

            offset_x = current_pos[0]
            offset_y = current_pos[1]
            offset_z = current_pos[2]

            # 2. Send the Venus-1 command to reset the hardware coordinates
            if self.send_command("0 0 0 setpos"):
                
                # 3. Shift all existing software barriers to match the new map
                # Math: New Barrier = Old Barrier - Offset
                if self.soft_limit_x_min is not None: 
                    self.soft_limit_x_min -= offset_x
                if self.soft_limit_x_max is not None: 
                    self.soft_limit_x_max -= offset_x
                if self.soft_limit_y_min is not None: 
                    self.soft_limit_y_min -= offset_y
                if self.soft_limit_y_max is not None: 
                    self.soft_limit_y_max -= offset_y
                if self.soft_limit_z_min is not None: 
                    self.soft_limit_z_min -= offset_z
                if self.soft_limit_z_max is not None: 
                    self.soft_limit_z_max -= offset_z

                print("Coordinate system reset to 0. Barriers shifted successfully.")
                return True
                
            return False
    
    def move_safe(self, target_x, target_y, target_z):
        """Moves the stage to the target position while respecting soft limits."""
        if self.soft_limit_x_min is not None and target_x < self.soft_limit_x_min:
            return False
        if self.soft_limit_x_max is not None and target_x > self.soft_limit_x_max:
            return False

        if self.soft_limit_y_min is not None and target_y < self.soft_limit_y_min:
            return False
        if self.soft_limit_y_max is not None and target_y > self.soft_limit_y_max:
            return False

        if self.soft_limit_z_min is not None and target_z < self.soft_limit_z_min:
            return False
        if self.soft_limit_z_max is not None and target_z > self.soft_limit_z_max:
            return False
        return True

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2.0)  # Set a timeout for connection attempts
            self.sock.connect((self.ip, self.port))
            self.connected = True
            print(f"Connected to Micos stage at {self.ip}:{self.port}")
            return True
        except Exception as e:
            print(f"Error connecting to Micos stage: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            self.connected = False
            print("Disconnected from Micos stage")

    def send_command(self, cmd):
        """Sends an ASCII string to controller. Venus-1 """
        if not self.connected:
            print("Not connected to Micos stage. Cannot send command.")
            return False
        try:
            full_cmd = f"{cmd}\r".encode('ascii')  # Append carriage return and encode to bytes
            time.sleep(0.05)
            self.sock.sendall(full_cmd)
            print(f"Sent command: {cmd}")
            return True
        except Exception as e:
            print(f"Error sending command to Micos stage: {e}")
            return False
        
    def move_relative(self, dx=0.0, dy=0.0, dz=0.0):
        """Moves the stage by the specified relative amounts."""
        current_pos = self.query_position()
        if not current_pos:
            print("Failed to query current position. Command not sent.")
            return False
        target_x = current_pos[0] + dx
        target_y = current_pos[1] + dy
        target_z = current_pos[2] + dz

        if not self.move_safe(target_x, target_y, target_z):
            print("Blocked, would hit artificial limits.")
            return False

        cmd = f"{dx} {dy} {dz} rmove"
        self.send_command("cerror")
        time.sleep(0.1)
        return self.send_command(cmd)
    
    def move_absolute(self, x=0.0, y=0.0, z=0.0):
        """Moves the stage to the specified absolute positions."""
        if not self.move_safe(x, y, z):
            print("Requested move exceeds soft limits. Command not sent.")
            return False
        cmd = f"{x} {y} {z} move"
        return self.send_command(cmd)
    
    def stop_motion(self):
        """Sends the stop command to halt any ongoing movement."""
        if self.connected:
            try:
                self.sock.sendall(b"\x03")  # Ctrl-C to stop motion
                print("Sent stop command to Micos stage.")
                return True
            except Exception as e:
                print(f"Stop command failed: {e}")
        return False
    
    def set_velocity(self, v_x, v_y, v_z ):
        """Sets the movement velocity. Venus-1 accepts a single velocity for all axes."""
        cmd = f"{v_x} {v_y} {v_z} setvel"
        return self.send_command(cmd)
    
    def get_error(self):
        """Queries the stage for any error messages."""
        if not self.connected:
            return "Not connected to Micos stage"
        try:
            self.sock.sendall(b"ge\r")
            response = self.sock.recv(1024).decode("ascii").strip()
            return response
        except Exception:
            return "Communication error while getting error message"
        
    def query_position(self):
        """Asks the stage for position, reading axis by axis with safety delays."""
        if not self.connected:
            return None
            
        try:
            self.sock.settimeout(0.05) 
            while True:
                try:
                    junk = self.sock.recv(1024)
                    if not junk: break
                except socket.timeout:
                    break
            
            self.sock.settimeout(1.0) 
            coords = [0.0, 0.0, 0.0]
            
            for i, axis in enumerate([1, 2, 3]):
                self.sock.sendall(f"{axis} pos\r".encode('ascii'))
                
                time.sleep(0.02) 
                
                response = self.sock.recv(1024).decode('ascii')
                clean_response = response.replace(">", "").strip()
                
                if clean_response:
                    coords[i] = float(clean_response)

            return (coords[0], coords[1], coords[2])
                
        except Exception as e:
            return None
    
    def home_axes(self):
        if not self.connected:
            print("Not connected to Micos stage. Cannot home axes.")
            return False
        self.send_command("cerror")
        time.sleep(0.1)

        return self.send_command("cal")