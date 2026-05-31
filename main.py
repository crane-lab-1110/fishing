import asyncio
import pygame
import sys
from game import Game

SCREEN_W = 1280
SCREEN_H = 720


async def main():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("つりスピ！ちゃお  ★ さかなつりゲーム ★")

    clock = pygame.time.Clock()
    game = Game(screen)

    while True:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            game.handle_event(event)

        game.update(dt)
        game.draw()
        pygame.display.flip()
        await asyncio.sleep(0)  # required for pygbag / browser


asyncio.run(main())
