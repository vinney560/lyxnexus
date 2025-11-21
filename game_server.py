from flask import Flask, render_template, jsonify, request
import ctypes
import json
import threading
import time

app = Flask(__name__)

# Load C game library
lib = ctypes.CDLL('./game_engine.so')

# Define C structures
class GameObject(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_double),
        ('y', ctypes.c_double),
        ('speed', ctypes.c_double),
        ('health', ctypes.c_int),
        ('is_alive', ctypes.c_int)
    ]

class GameState(ctypes.Structure):
    _fields_ = [
        ('player', GameObject),
        ('enemies', GameObject * 20),
        ('bullets', GameObject * 10),
        ('score', ctypes.c_int),
        ('level', ctypes.c_int),
        ('game_over', ctypes.c_int),
        ('enemies_killed', ctypes.c_int)
    ]

# Setup C function signatures
lib.init_game.argtypes = [ctypes.POINTER(GameState)]
lib.move_player.argtypes = [ctypes.POINTER(GameState), ctypes.c_char_p]
lib.player_shoot.argtypes = [ctypes.POINTER(GameState)]
lib.update_game.argtypes = [ctypes.POINTER(GameState)]
lib.get_game_state_json.argtypes = [ctypes.POINTER(GameState), ctypes.c_char_p, ctypes.c_int]

# Global game state
game_state = GameState()
lib.init_game(ctypes.byref(game_state))

def game_loop():
    """Main game loop running in background"""
    while True:
        lib.update_game(ctypes.byref(game_state))
        time.sleep(0.033)  # ~30 FPS

# Start game loop thread
game_thread = threading.Thread(target=game_loop, daemon=True)
game_thread.start()

@app.route('/')
def index():
    return render_template('game.html')

@app.route('/api/game/state')
def get_game_state():
    """Get current game state"""
    buffer = ctypes.create_string_buffer(1024)
    lib.get_game_state_json(ctypes.byref(game_state), buffer, 1024)
    
    state_json = json.loads(buffer.value.decode())
    
    # Add enemies and bullets data
    enemies = []
    for i in range(20):
        enemy = game_state.enemies[i]
        if enemy.is_alive:
            enemies.append({'x': enemy.x, 'y': enemy.y})
    
    bullets = []
    for i in range(10):
        bullet = game_state.bullets[i]
        if bullet.is_alive:
            bullets.append({'x': bullet.x, 'y': bullet.y})
    
    state_json['enemies'] = enemies
    state_json['bullets'] = bullets
    
    return jsonify(state_json)

@app.route('/api/game/move', methods=['POST'])
def move_player():
    """Move player"""
    direction = request.json.get('direction')
    if direction in ['left', 'right', 'up', 'down']:
        lib.move_player(ctypes.byref(game_state), direction.encode())
    return jsonify({'status': 'ok'})

@app.route('/api/game/shoot', methods=['POST'])
def shoot():
    """Player shooting"""
    lib.player_shoot(ctypes.byref(game_state))
    return jsonify({'status': 'ok'})

@app.route('/api/game/reset', methods=['POST'])
def reset_game():
    """Reset game"""
    lib.init_game(ctypes.byref(game_state))
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)