"""
Data Loading Utilities for Message Notification Router

Handles loading all CSV files and providing easy access to:
- Messages (test and samples)
- Users, Groups, Businesses
- Message history and events
- Media files (images, audio)
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import os


class DatasetLoader:
    """Load and manage all competition datasets"""

    def __init__(self, dataset_path: str = "../dataset"):
        """
        Initialize dataset loader

        Args:
            dataset_path: Path to dataset/ directory
        """
        self.dataset_path = Path(dataset_path)
        self._validate_paths()

        # Will be populated on first access
        self._messages = None
        self._samples = None
        self._users = None
        self._groups = None
        self._businesses = None
        self._message_history = None
        self._message_events = None
        self._images = None
        self._voice_notes = None
        self._group_members = None
        self._user_business_history = None
        self._daily_summary = None

    def _validate_paths(self):
        """Ensure dataset directory exists"""
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset path not found: {self.dataset_path}")

    @property
    def messages(self) -> pd.DataFrame:
        """Load test messages (264 rows to predict)"""
        if self._messages is None:
            self._messages = pd.read_csv(self.dataset_path / "messages.csv")
            print(f"[+] Loaded {len(self._messages)} test messages")
        return self._messages

    @property
    def samples(self) -> pd.DataFrame:
        """Load sample messages with labels (70 training examples)"""
        if self._samples is None:
            self._samples = pd.read_csv(self.dataset_path / "sample_messages.csv")
            print(f"[+] Loaded {len(self._samples)} sample messages (training data)")
        return self._samples

    @property
    def users(self) -> pd.DataFrame:
        """Load user metadata (54 users)"""
        if self._users is None:
            self._users = pd.read_csv(self.dataset_path / "users.csv")
            print(f"[+] Loaded {len(self._users)} users")
        return self._users

    @property
    def groups(self) -> pd.DataFrame:
        """Load group metadata (23 groups)"""
        if self._groups is None:
            self._groups = pd.read_csv(self.dataset_path / "groups.csv")
            print(f"[+] Loaded {len(self._groups)} groups")
        return self._groups

    @property
    def businesses(self) -> pd.DataFrame:
        """Load business account metadata (110 businesses)"""
        if self._businesses is None:
            self._businesses = pd.read_csv(self.dataset_path / "business_accounts.csv")
            print(f"[+] Loaded {len(self._businesses)} business accounts")
        return self._businesses

    @property
    def message_history(self) -> pd.DataFrame:
        """Load historical messages (1,062 messages)"""
        if self._message_history is None:
            self._message_history = pd.read_csv(self.dataset_path / "message_history.csv")
            print(f"[+] Loaded {len(self._message_history)} historical messages")
        return self._message_history

    @property
    def message_events(self) -> pd.DataFrame:
        """Load user reactions to messages (opened, replied, dismissed, etc.)"""
        if self._message_events is None:
            self._message_events = pd.read_csv(self.dataset_path / "message_events.csv")
            print(f"[+] Loaded {len(self._message_events)} message events")
        return self._message_events

    @property
    def images(self) -> pd.DataFrame:
        """Load image metadata (20 images)"""
        if self._images is None:
            self._images = pd.read_csv(self.dataset_path / "images.csv")
            print(f"[+] Loaded {len(self._images)} images")
        return self._images

    @property
    def voice_notes(self) -> pd.DataFrame:
        """Load voice note metadata (13 audio files)"""
        if self._voice_notes is None:
            self._voice_notes = pd.read_csv(self.dataset_path / "voice_notes.csv")
            print(f"[+] Loaded {len(self._voice_notes)} voice notes")
        return self._voice_notes

    @property
    def group_members(self) -> pd.DataFrame:
        """Load user-group relationships"""
        if self._group_members is None:
            self._group_members = pd.read_csv(self.dataset_path / "group_members.csv")
            print(f"[+] Loaded {len(self._group_members)} group member records")
        return self._group_members

    @property
    def user_business_history(self) -> pd.DataFrame:
        """Load user-business interaction history"""
        if self._user_business_history is None:
            self._user_business_history = pd.read_csv(self.dataset_path / "user_business_history.csv")
            print(f"[+] Loaded {len(self._user_business_history)} user-business records")
        return self._user_business_history

    @property
    def daily_summary(self) -> pd.DataFrame:
        """Load daily notification summary"""
        if self._daily_summary is None:
            self._daily_summary = pd.read_csv(self.dataset_path / "daily_notification_summary.csv")
            print(f"[+] Loaded {len(self._daily_summary)} daily summary records")
        return self._daily_summary

    def get_media_path(self, media_type: str, media_id: str) -> Optional[Path]:
        """
        Get full path to media file

        Args:
            media_type: 'image' or 'voice'
            media_id: Image or voice note ID

        Returns:
            Full path to media file, or None if not found
        """
        if media_type == 'image':
            # Look up in images.csv
            img_row = self.images[self.images['image_id'] == media_id]
            if len(img_row) == 0:
                return None
            file_path = img_row.iloc[0]['file_path']
            return self.dataset_path / file_path

        elif media_type == 'voice':
            # Look up in voice_notes.csv
            voice_row = self.voice_notes[self.voice_notes['voice_note_id'] == media_id]
            if len(voice_row) == 0:
                return None
            file_path = voice_row.iloc[0]['file_path']
            return self.dataset_path / file_path

        return None

    def summary(self) -> Dict[str, int]:
        """Get dataset summary statistics"""
        return {
            'test_messages': len(self.messages),
            'sample_messages': len(self.samples),
            'users': len(self.users),
            'groups': len(self.groups),
            'businesses': len(self.businesses),
            'message_history': len(self.message_history),
            'message_events': len(self.message_events),
            'images': len(self.images),
            'voice_notes': len(self.voice_notes),
            'group_members': len(self.group_members),
            'user_business_history': len(self.user_business_history),
        }


def quick_load(dataset_path: str = "../dataset") -> DatasetLoader:
    """
    Quick function to create a data loader

    Usage:
        data = quick_load()
        messages = data.messages
        samples = data.samples
    """
    return DatasetLoader(dataset_path)


if __name__ == "__main__":
    # Test loading
    print("Testing DatasetLoader...")
    data = quick_load()

    print("\n📊 Dataset Summary:")
    for name, count in data.summary().items():
        print(f"  {name}: {count}")

    print("\n[+] All datasets loaded successfully!")
