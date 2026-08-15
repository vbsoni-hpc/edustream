"""
Bootstrap script — runs before servers start on Render.

Sequence:
  1. Init DB tables
  2. Restore backup from Telegram Saved Messages (users, structure, progress)
  3. Sync videos from Telegram channel
  4. Re-apply module assignments from backup
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BOOTSTRAP] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def run_bootstrap():
    """Full bootstrap sequence."""
    from backend.models import init_db
    from backend.telegram_client import get_client, sync_channel, disconnect
    from backend.telegram_backup import restore_from_telegram, apply_pending_assignments
    from config import DEFAULT_SEGMENT_ICONS

    # Step 1: Init database
    logger.info("Step 1/4: Initialising database...")
    init_db()

    # Step 2: Restore from Telegram backup
    logger.info("Step 2/4: Restoring backup from Telegram Saved Messages...")
    restored = await restore_from_telegram()
    if restored:
        logger.info("  ✔ Backup restored successfully")
    else:
        logger.info("  ℹ No backup found — fresh start")

    # Step 3: Sync videos from Telegram channel
    logger.info("Step 3/4: Syncing videos from Telegram channel...")
    try:
        from backend.models import get_or_create_segment, upsert_video
        videos = await sync_channel()
        synced = 0
        for v in videos:
            segment_name = v["segment"]
            icon = DEFAULT_SEGMENT_ICONS.get(segment_name, "📁")
            segment_id = get_or_create_segment(segment_name, icon)
            upsert_video(
                telegram_msg_id=v["telegram_msg_id"],
                title=v["title"],
                segment_id=segment_id,
                duration_sec=v["duration_sec"],
                file_size=v["file_size"],
                mime_type=v["mime_type"],
                caption=v["caption"],
            )
            synced += 1
        logger.info(f"  ✔ Synced {synced} videos")
    except Exception as e:
        logger.error(f"  ✘ Sync failed: {e}")

    # Step 4: Re-apply module assignments from backup
    logger.info("Step 4/4: Applying module assignments from backup...")
    apply_pending_assignments()
    logger.info("  ✔ Done")

    # Disconnect Telegram client (servers will create their own)
    await disconnect()
    logger.info("Bootstrap complete!")


def main():
    """Entry point for `python -m backend.bootstrap`."""
    logger.info("=" * 60)
    logger.info("  EduStream Bootstrap — Restore & Sync")
    logger.info("=" * 60)

    try:
        asyncio.run(run_bootstrap())
    except KeyboardInterrupt:
        logger.info("Bootstrap interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}")
        # Don't exit with error — let the servers start anyway
        # The app will work, just without restored data
        logger.info("Continuing with empty database...")


if __name__ == "__main__":
    main()
