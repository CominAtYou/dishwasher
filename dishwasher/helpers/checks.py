import config
from helpers.sv_config import get_config


def check_if_staff(ctx):
    if ctx.author.id in config.bot_managers:
        return True
    if not ctx.guild:
        return False
    return any(
        any(
            r.id == get_config(ctx.guild.id, "staff", "staff_role")
            for r in ctx.author.roles
        ),
        any(m == ctx.author.id for m in config.bot_managers),
        ctx.author.guild_permissions.manage_guild,
    )


def check_if_bot_manager(ctx):
    return any(m == ctx.author.id for m in config.bot_managers)
