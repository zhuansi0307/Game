"""
状态UI组件
负责显示主角属性和NPC好感度
"""

import pygame
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_CHAMPAGNE, COLOR_PANEL, COLOR_PANEL_BORDER
from engine.game_state import get_game_state
from engine.asset_manager import AssetManager


class StatusUI:
    """角色状态UI组件"""

    def __init__(self):
        self.visible = True
        self.asset_manager = AssetManager()
        self.font_small = self.asset_manager.load_font(24) if self.asset_manager else pygame.font.Font(None, 24)
        self.font_medium = self.asset_manager.load_font(28) if self.asset_manager else pygame.font.Font(None, 28)

    def update(self, dt):
        """更新UI（预留）"""
        pass

    def draw(self, screen):
        """绘制状态UI"""
        if not self.visible:
            return

        gs = get_game_state()
        
        # 面板设置
        panel_width = 250
        panel_height = 158
        
        # 如果有多个NPC，高度可以动态增加
        npc_count = len(gs.npc_affections)
        if npc_count > 0:
            panel_height += 35 * npc_count + 15

        panel_x = 30
        panel_y = 94
        
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((*COLOR_PANEL, 200))
        pygame.draw.rect(panel_surface, (*COLOR_PANEL_BORDER, 255), 
                         (0, 0, panel_width, panel_height), 1, border_radius=8)
        
        screen.blit(panel_surface, (panel_x, panel_y))
        
        # 绘制标题
        title_surface = self.font_medium.render("角色状态", True, COLOR_CHAMPAGNE)
        screen.blit(title_surface, (panel_x + 15, panel_y + 15))
        
        # 绘制主角属性
        y_offset = panel_y + 50
        intel = gs.get_player_stat("intelligence")
        stam = gs.get_player_stat("stamina")
        money = gs.get_player_stat("money")
        
        stat_surface_intel = self.font_small.render(f"智力: {intel}", True, COLOR_TEXT)
        screen.blit(stat_surface_intel, (panel_x + 20, y_offset))
        y_offset += 30
        
        stat_surface_stam = self.font_small.render(f"体力: {stam}/100", True, COLOR_TEXT)
        screen.blit(stat_surface_stam, (panel_x + 20, y_offset))
        y_offset += 30

        stat_surface_money = self.font_small.render(f"余额: {money}", True, COLOR_TEXT)
        screen.blit(stat_surface_money, (panel_x + 20, y_offset))
        y_offset += 30
        
        # 绘制NPC好感度
        if npc_count > 0:
            pygame.draw.line(screen, COLOR_PANEL_BORDER, (panel_x + 15, y_offset), (panel_x + panel_width - 15, y_offset))
            y_offset += 15
            for npc_id, affection in gs.npc_affections.items():
                npc_surface = self.font_small.render(f"{npc_id} 好感度: {affection}", True, COLOR_TEXT)
                screen.blit(npc_surface, (panel_x + 20, y_offset))
                y_offset += 30
