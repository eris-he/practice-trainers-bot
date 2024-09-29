import discord
from typing import Callable, Optional


class Pagination(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, get_page: Callable, total_days: int, events):
        self.interaction = interaction
        self.get_page = get_page
        self.total_days = total_days  # Number of days to paginate
        self.events = events
        self.index = 1  # Page index starts at 1 (Day 1)
        self.page_index = 1  # Page index within a single day
        self.total_pages_for_day = 1  # Tracks total pages for the current day
        super().__init__(timeout=100)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # if interaction.user == self.interaction.user:
        #     return True
        # else:
        #     emb = discord.Embed(
        #         description=f"Only the author of the command can perform this action.",
        #         color=16711680
        #     )
        #     await interaction.response.send_message(embed=emb, ephemeral=True)
        #     return False
        return True

    async def navigate(self):
        # Fetch the first page of events for the first day
        embed, self.total_pages_for_day = await self.get_page(self.events, day_index=self.index)
        self.page_index = 1  # Start at the first page within the day

        if self.total_pages_for_day == 1 and self.total_days == 1:
            await self.interaction.response.send_message(embed=embed)
        else:
            self.update_buttons()
            await self.interaction.response.send_message(embed=embed, view=self)

    async def edit_page(self, interaction: discord.Interaction):
        # Fetch the current page of events for the current day
        embed, total_pages_for_day = await self.get_page(self.events, day_index=self.index, page_index=self.page_index)
        self.total_pages_for_day = total_pages_for_day
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    def update_buttons(self):
        # Disable buttons appropriately based on the current day/page
        self.children[0].disabled = self.index == 1 and self.page_index == 1  # Disable 'previous' if on the first page of the first day
        self.children[1].disabled = self.index == self.total_days and self.page_index == self.total_pages_for_day  # Disable 'next' if on the last page of the last day

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.Button):
        # Handle navigating to the previous page/day
        if self.page_index > 1:
            # Go to the previous page within the same day
            self.page_index -= 1
        elif self.index > 1:
            # Go to the previous day and its last page
            self.index -= 1
            embed, self.total_pages_for_day = await self.get_page(self.events, day_index=self.index)
            self.page_index = self.total_pages_for_day  # Go to the last page of the previous day
        await self.edit_page(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.Button):
        # Handle navigating to the next page/day
        if self.page_index < self.total_pages_for_day:
            # Go to the next page within the same day
            self.page_index += 1
        elif self.index < self.total_days:
            # Go to the next day and start at its first page
            self.index += 1
            self.page_index = 1
        await self.edit_page(interaction)

    async def on_timeout(self):
        # Remove buttons on timeout
        message = await self.interaction.original_response()
        await message.edit(view=None)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return ((total_results - 1) // results_per_page) + 1
