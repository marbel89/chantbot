"""
Discord bot for anonymous message posting.

Allows users to DM the bot, confirm their submission, and have it posted
anonymously to a designated channel. Submissions are logged for moderators.
"""
import discord
from discord.ext import commands
from discord import ui
import os
from dotenv import load_dotenv
import io

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANONYMOUS_CHANNEL_ID = os.getenv("ANONYMOUS_CHANNEL_ID")
MOD_LOG_CHANNEL_ID = os.getenv("MOD_LOG_CHANNEL_ID")

# Validate essential configuration
if not DISCORD_TOKEN:
    print("CRITICAL: DISCORD_TOKEN not found in .env")
    exit()
if not ANONYMOUS_CHANNEL_ID:
    print("CRITICAL: ANONYMOUS_CHANNEL_ID not found in .env")
    exit()
else:
    try:
        ANONYMOUS_CHANNEL_ID = int(ANONYMOUS_CHANNEL_ID)
    except ValueError:
        print(f"CRITICAL: Invalid ANONYMOUS_CHANNEL_ID '{ANONYMOUS_CHANNEL_ID}'. Must be an integer.")
        exit()

if not MOD_LOG_CHANNEL_ID:
    print("CRITICAL: MOD_LOG_CHANNEL_ID not found in .env")
    exit()
else:
    try:
        MOD_LOG_CHANNEL_ID = int(MOD_LOG_CHANNEL_ID)
    except ValueError:
        print(f"CRITICAL: Invalid MOD_LOG_CHANNEL_ID '{MOD_LOG_CHANNEL_ID}'. Must be an integer.")
        exit()

# Define Discord Gateway Intents
intents = discord.Intents.default()
intents.messages = True          # Required for message events
intents.message_content = True   # Required to read message content (Privileged Intent)
intents.guilds = True            # For guild information (e.g., fetching channels)
intents.dm_messages = True       # To receive DM events

# Bot instance. No prefix needed if primarily DM-based for submissions.
# Using when_mentioned_or as a fallback prefix for potential admin commands.
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!anon-"), intents=intents)

# --- UI View for Submission Confirmation ---
class ConfirmationView(ui.View):
    """
    A view with buttons for users to confirm or cancel their anonymous post.
    Associated with a specific user's DM.
    """
    def __init__(self, original_message: discord.Message):
        super().__init__(timeout=300)  # 5-minute timeout for user interaction
        self.original_message = original_message # The user's DM to be posted
        self.confirmed_post = None # Stores user's choice: True (post), False (cancel)
        self.message = None # Stores the bot's message this view is attached to

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original message author can interact with the buttons."""
        return interaction.user.id == self.original_message.author.id

    async def on_timeout(self):
        """Handles view timeout: disables buttons and updates the confirmation message."""
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
        try:
            if self.message:
                 await self.message.edit(content="This anonymous post request has timed out.", view=self)
        except discord.NotFound:
            # Original message might have been deleted by user or bot
            pass
        except Exception as e:
            # Log other potential errors during timeout message edit
            print(f"Error editing message on ConfirmationView timeout: {e}")
        self.stop() # Important to stop the view from listening further
        # print(f"ConfirmationView for {self.original_message.author} timed out.") # Dev log

    @ui.button(label="Post Anonymously", style=discord.ButtonStyle.green, custom_id="confirm_post_anon")
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handles the 'Post Anonymously' button click."""
        self.confirmed_post = True
        for item in self.children:
            item.disabled = True
        # Acknowledge interaction immediately, then process
        await interaction.response.edit_message(content="Processing your request...", view=self)
        self.stop()

    @ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel_post_anon")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handles the 'Cancel' button click."""
        self.confirmed_post = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Request cancelled.", view=self)
        self.stop()

# --- Bot Event Handlers ---
@bot.event
async def on_ready():
    """Called when the bot is fully connected and ready."""
    print(f'{bot.user.name} (ID: {bot.user.id}) is online.')
    print(f"Anonymous Channel: {ANONYMOUS_CHANNEL_ID}")
    print(f"Mod Log Channel: {MOD_LOG_CHANNEL_ID}")

    # Verify channel accessibility on startup
    anon_channel = bot.get_channel(ANONYMOUS_CHANNEL_ID)
    mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if not anon_channel:
        print(f"WARNING: Could not find anonymous channel (ID: {ANONYMOUS_CHANNEL_ID}).")
    if not mod_channel:
        print(f"WARNING: Could not find mod log channel (ID: {MOD_LOG_CHANNEL_ID}).")

@bot.event
async def on_message(message: discord.Message):
    """Handles incoming messages, focusing on DMs for anonymous submissions."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Process only DMs for anonymous submissions
    if isinstance(message.channel, discord.DMChannel):
        # Message must have text or attachments to be submittable
        if not message.content and not message.attachments:
            await message.author.send("Your message must contain text or an attachment to be posted.")
            return

        # print(f"DM received from {message.author} (ID: {message.author.id})") # Dev log

        # Present confirmation options to the user
        view = ConfirmationView(original_message=message)
        confirmation_text = "Do you want to post the content anonymously?"
        if message.attachments:
            confirmation_text += f"\n(You have {len(message.attachments)} attachment(s))"
        
        sent_confirmation_msg = await message.author.send(confirmation_text, view=view)
        view.message = sent_confirmation_msg # Link view to its sent message for later edits

        await view.wait() # Wait for user interaction or timeout

        # --- Process based on user's choice in the ConfirmationView ---
        if view.confirmed_post is True:
            # print(f"User {message.author} confirmed submission.") # Dev log
            anon_channel = bot.get_channel(ANONYMOUS_CHANNEL_ID)
            mod_log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)

            if not anon_channel:
                print(f"ERROR: Anonymous channel {ANONYMOUS_CHANNEL_ID} not found during post attempt.")
                # User already sees "Processing...", update it to failure
                if view.message: await view.message.edit(content="Failed to post: Anonymous channel not configured correctly. Admin notified.", view=None)
                else: await message.author.send("Failed to post: Anonymous channel not configured correctly. Admin notified.")
                return

            # Prepare content for anonymous post
            embed_description = view.original_message.content
            files_to_send = []
            posted_anon_message = None # Will store the Message object of the anonymous post

            if view.original_message.attachments:
                for attachment in view.original_message.attachments:
                    try:
                        image_bytes = await attachment.read()
                        discord_file = discord.File(io.BytesIO(image_bytes), filename=attachment.filename)
                        files_to_send.append(discord_file)
                    except Exception as e:
                        print(f"ERROR: Failed to read attachment '{attachment.filename}' from user {message.author.id}: {e}")
                        # Inform user specifically about this attachment failure
                        await message.author.send(f"Sorry, I couldn't process the attachment: {attachment.filename}. It will be skipped.")
            
            # Prevent posting empty messages (e.g. if text is empty and all attachments failed)
            if not embed_description and not files_to_send:
                # print(f"User {message.author} tried to post an effectively empty message.") # Dev log
                if view.message: await view.message.edit(content="Your message was empty or attachments could not be processed. Nothing was posted.", view=None)
                else: await message.author.send("Your message was empty or attachments could not be processed. Nothing was posted.")
                return

            anon_embed = discord.Embed(
                description=embed_description if embed_description else None, # Embed description is optional if images are present
                color=discord.Color.blue() # Or any other preferred color
            )

            try:
                # Post to anonymous channel
                if files_to_send:
                    posted_anon_message = await anon_channel.send(embed=anon_embed if embed_description else None, files=files_to_send)
                elif embed_description: # Only text content
                    posted_anon_message = await anon_channel.send(embed=anon_embed)
                
                # Update user's confirmation message to success
                if view.message:
                    await view.message.edit(content=f"Your message has been posted anonymously to #{anon_channel.name}!", view=None)
                else: # Fallback DM if original confirmation message is gone for some reason
                    await message.author.send(f"Your message has been posted anonymously to #{anon_channel.name}!")
                # print(f"Posted anonymously for {message.author.id} to #{anon_channel.name}") # Dev log

                # Log to moderator channel
                if not mod_log_channel:
                    print(f"ERROR: Mod log channel {MOD_LOG_CHANNEL_ID} not found. Post by {message.author.id} was not logged.")
                else:
                    log_embed = discord.Embed(
                        title="Anonymous Post Logged",
                        color=discord.Color.orange(),
                        timestamp=view.original_message.created_at # Timestamp of the original user DM
                    )
                    log_embed.set_author(
                        name=f"{view.original_message.author.name} (ID: {view.original_message.author.id})",
                        icon_url=view.original_message.author.display_avatar.url if view.original_message.author.display_avatar else None
                    )
                    log_embed.add_field(
                        name="Original Content",
                        value=view.original_message.content if view.original_message.content else "*(No text content)*",
                        inline=False
                    )
                    if view.original_message.attachments:
                        attachment_links = [f"[Attachment {i+1}]({att.url}) (`{att.filename}`)" for i, att in enumerate(view.original_message.attachments)]
                        log_embed.add_field(name="Original Attachments", value="\n".join(attachment_links), inline=False)
                    
                    if posted_anon_message: # Link to the anonymously posted message
                        log_embed.add_field(name="Posted Message", value=f"[Jump to Message]({posted_anon_message.jump_url}) in #{anon_channel.name}", inline=False)
                    else: # Should not happen if posting was successful
                        log_embed.set_footer(text=f"Posted to: #{anon_channel.name} (Error retrieving jump link)")
                    
                    try:
                        await mod_log_channel.send(embed=log_embed)
                        # print(f"Logged post from {message.author.id} to #{mod_log_channel.name}") # Dev log
                    except discord.Forbidden:
                        print(f"ERROR: Bot lacks Send Messages/Embed Links permission in Mod Log Channel #{mod_log_channel.name}.")
                    except discord.HTTPException as e:
                        print(f"ERROR: Failed to send log to mod log channel for post by {message.author.id}: {e}")

            except discord.Forbidden:
                print(f"ERROR: Bot lacks Send Messages/Embed Links/Attach Files permission in Anonymous Channel #{anon_channel.name}.")
                if view.message: await view.message.edit(content="Failed to post. Bot permission error in the anonymous channel. Admin notified.", view=None)
                else: await message.author.send("Failed to post. Bot permission error in the anonymous channel. Admin notified.")
            except discord.HTTPException as e:
                print(f"ERROR: Network error occurred sending to anonymous channel for {message.author.id}: {e}")
                if view.message: await view.message.edit(content="Failed to post. A network error occurred. Please try again.", view=None)
                else: await message.author.send("Failed to post. A network error occurred. Please try again.")
            except Exception as e: # Catch any other unexpected errors during posting
                print(f"CRITICAL: An unexpected error occurred during anonymous posting for {message.author.id}: {e}")
                # Provide a generic error message to the user but log the detailed error
                if view.message: await view.message.edit(content="Failed to post due to an unexpected error. Admin has been notified.", view=None)
                else: await message.author.send("Failed to post due to an unexpected error. Admin has been notified.")

        elif view.confirmed_post is False:
            # User cancelled, message already updated by the view
            # print(f"User {message.author.id} cancelled post request.") # Dev log
            pass
        else: # Timeout
            # User did not interact in time, message updated by on_timeout
            # print(f"Anonymous post request from {message.author.id} timed out.") # Dev log
            pass
    
    # Allow processing of bot commands if any are defined with the chosen prefix
    await bot.process_commands(message)


# --- Main Execution ---
if __name__ == "__main__":
    print("Starting anonymous posting bot...")
    bot.run(DISCORD_TOKEN)