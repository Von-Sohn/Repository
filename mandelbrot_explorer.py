import pygame
import numpy as np
import threading

# Optional: Import Numba for performance optimization
try:
    from numba import njit, prange
    USE_NUMBA = True
except ImportError:
    USE_NUMBA = False
    print("Numba is not installed. The program will run without optimization. Install Numba for better performance.")

# Initialize Pygame
pygame.init()

# Set up display
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Interactive Mandelbrot Fractal Explorer")

# Define the initial view (complex plane boundaries)
RE_START, RE_END = -2.5, 1.5
IM_START, IM_END = -1.5, 1.5

# Maximum iterations for Mandelbrot calculation
MAX_ITER = 256

# Variables for threading
render_thread = None
needs_render = False
render_lock = threading.Lock()

# Compute the Mandelbrot set
def compute_mandelbrot(re_start, re_end, im_start, im_end, width, height, max_iter):
    if USE_NUMBA:
        return compute_mandelbrot_numba(re_start, re_end, im_start, im_end, width, height, max_iter)
    else:
        return compute_mandelbrot_plain(re_start, re_end, im_start, im_end, width, height, max_iter)

# Mandelbrot computation with Numba for optimization
if USE_NUMBA:
    @njit(parallel=True)
    def compute_mandelbrot_numba(re_start, re_end, im_start, im_end, width, height, max_iter):
        image = np.zeros((height, width, 3), dtype=np.uint8)
        pixel_size_x = (re_end - re_start) / width
        pixel_size_y = (im_end - im_start) / height
        for y in prange(height):
            c_im = im_start + y * pixel_size_y
            for x in prange(width):
                c_re = re_start + x * pixel_size_x
                c = complex(c_re, c_im)
                z = 0j
                n = 0
                while abs(z) <= 2 and n < max_iter:
                    z = z * z + c
                    n += 1
                color = 255 - int(n * 255 / max_iter)
                image[y, x] = (color, color, color)
        return image
else:
    def compute_mandelbrot_plain(re_start, re_end, im_start, im_end, width, height, max_iter):
        image = np.zeros((height, width, 3), dtype=np.uint8)
        pixel_size_x = (re_end - re_start) / width
        pixel_size_y = (im_end - im_start) / height
        for y in range(height):
            c_im = im_start + y * pixel_size_y
            for x in range(width):
                c_re = re_start + x * pixel_size_x
                c = complex(c_re, c_im)
                z = 0j
                n = 0
                while abs(z) <= 2 and n < max_iter:
                    z = z * z + c
                    n += 1
                color = 255 - int(n * 255 / max_iter)
                image[y, x] = (color, color, color)
        return image

# Initial Mandelbrot computation
mandelbrot_surface = None

def update_mandelbrot():
    global mandelbrot_surface, needs_render, render_thread

    def render():
        global mandelbrot_surface, needs_render
        with render_lock:
            mandelbrot_array = compute_mandelbrot(RE_START, RE_END, IM_START, IM_END, WIDTH, HEIGHT, MAX_ITER)
            mandelbrot_surface = pygame.surfarray.make_surface(np.rot90(mandelbrot_array))
            needs_render = False

    if render_thread and render_thread.is_alive():
        return  # Rendering is already in progress
    else:
        needs_render = True
        render_thread = threading.Thread(target=render)
        render_thread.start()

update_mandelbrot()

# Main loop variables
running = True
dragging = False
last_mouse_pos = None
zoom_factor = 1.0

clock = pygame.time.Clock()

# Main event loop
while running:
    dt = clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Start dragging
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                dragging = True
                last_mouse_pos = event.pos

        # Stop dragging
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left click
                dragging = False

        # Mouse movement
        elif event.type == pygame.MOUSEMOTION:
            if dragging:
                dx = event.pos[0] - last_mouse_pos[0]
                dy = event.pos[1] - last_mouse_pos[1]
                last_mouse_pos = event.pos

                # Convert pixel movement to coordinate movement (correct direction)
                re_range = RE_END - RE_START
                im_range = IM_END - IM_START
                RE_START += dx * re_range / WIDTH
                RE_END += dx * re_range / WIDTH
                IM_START -= dy * im_range / HEIGHT
                IM_END -= dy * im_range / HEIGHT

                update_mandelbrot()

        # Zoom with scroll wheel
        elif event.type == pygame.MOUSEWHEEL:
            zoom_scale = 0.1
            zoom = 1 - zoom_scale * event.y  # event.y is +1 or -1 depending on scroll direction

            mouse_x, mouse_y = pygame.mouse.get_pos()

            re_range = RE_END - RE_START
            im_range = IM_END - IM_START
            c_re = RE_START + mouse_x * re_range / WIDTH
            c_im = IM_START + mouse_y * im_range / HEIGHT

            RE_START = c_re - (c_re - RE_START) * zoom
            RE_END = c_re + (RE_END - c_re) * zoom
            IM_START = c_im - (c_im - IM_START) * zoom
            IM_END = c_im + (IM_END - c_im) * zoom

            update_mandelbrot()

    if mandelbrot_surface:
        screen.blit(mandelbrot_surface, (0, 0))

    pygame.display.flip()

pygame.quit()