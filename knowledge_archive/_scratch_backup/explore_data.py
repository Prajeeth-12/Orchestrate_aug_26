"""
Comprehensive Data Exploration Script for Message Notification Router Competition

This script explores all available datasets to understand:
- Distribution of actions, message types, conversation types
- Confidence score ranges
- Media type distribution
- Evidence message coverage
- Data quality issues
- Key statistics for users, groups, businesses

Outputs: exploration_results.txt with detailed findings
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from collections import Counter
from typing import Dict, List, Tuple

# Add utils to path
sys.path.append(str(Path(__file__).parent))
from utils.data_loader import DatasetLoader


class DataExplorer:
    """Comprehensive data exploration for Message Notification Router"""

    def __init__(self, dataset_path: str = "../dataset"):
        """Initialize with dataset loader"""
        print("=" * 80)
        print("MESSAGE NOTIFICATION ROUTER - DATA EXPLORATION")
        print("=" * 80)
        print()

        self.loader = DatasetLoader(dataset_path)
        self.findings = []

        # Track matplotlib availability
        self.has_matplotlib = False
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            self.plt = plt
            self.has_matplotlib = True
            print("[+] Matplotlib available - will generate visualizations")
        except ImportError:
            print("[-] Matplotlib not available - will use text summaries only")

        print()

    def add_finding(self, title: str, content: str):
        """Add a finding to the report"""
        self.findings.append(f"\n{'=' * 80}\n{title}\n{'=' * 80}\n{content}\n")
        print(f"\n{title}")
        print("-" * 80)
        print(content)

    def explore_samples(self):
        """Explore sample_messages.csv (training data)"""
        samples = self.loader.samples

        # Action distribution
        action_counts = samples['action'].value_counts()
        action_pct = (action_counts / len(samples) * 100).round(2)

        action_summary = "ACTION DISTRIBUTION (Training Data)\n\n"
        action_summary += f"Total samples: {len(samples)}\n\n"
        for action in ['notify', 'digest', 'mute']:
            count = action_counts.get(action, 0)
            pct = action_pct.get(action, 0)
            action_summary += f"  {action:8s}: {count:3d} samples ({pct:5.1f}%)\n"

        self.add_finding("1. SAMPLE ACTIONS DISTRIBUTION", action_summary)

        # Message type in samples
        msg_type_counts = samples['message_type'].value_counts()
        msg_type_summary = "MESSAGE TYPE DISTRIBUTION (Training Data)\n\n"
        for msg_type, count in msg_type_counts.items():
            pct = count / len(samples) * 100
            msg_type_summary += f"  {msg_type}: {count} ({pct:.1f}%)\n"

        self.add_finding("2. MESSAGE TYPES IN SAMPLES", msg_type_summary)

        # Confidence scores by action
        conf_summary = "CONFIDENCE SCORE RANGES BY ACTION\n\n"
        for action in ['notify', 'digest', 'mute']:
            action_samples = samples[samples['action'] == action]
            if len(action_samples) > 0:
                conf_scores = action_samples['confidence']
                conf_summary += f"{action.upper()}:\n"
                conf_summary += f"  Min:     {conf_scores.min():.3f}\n"
                conf_summary += f"  Max:     {conf_scores.max():.3f}\n"
                conf_summary += f"  Mean:    {conf_scores.mean():.3f}\n"
                conf_summary += f"  Median:  {conf_scores.median():.3f}\n"
                conf_summary += f"  Std Dev: {conf_scores.std():.3f}\n\n"

        self.add_finding("3. CONFIDENCE SCORE ANALYSIS", conf_summary)

        # Evidence message IDs coverage
        has_evidence = samples['evidence_message_ids'].notna() & (samples['evidence_message_ids'] != 'none')
        evidence_count = has_evidence.sum()
        evidence_pct = evidence_count / len(samples) * 100

        evidence_summary = f"Total samples with evidence: {evidence_count} / {len(samples)} ({evidence_pct:.1f}%)\n"
        evidence_summary += f"Samples without evidence: {len(samples) - evidence_count} ({100 - evidence_pct:.1f}%)\n\n"

        # Average number of evidence messages
        evidence_lengths = samples[has_evidence]['evidence_message_ids'].apply(
            lambda x: len(str(x).split(',')) if pd.notna(x) else 0
        )
        if len(evidence_lengths) > 0:
            evidence_summary += f"Average evidence messages per sample: {evidence_lengths.mean():.1f}\n"
            evidence_summary += f"Max evidence messages: {evidence_lengths.max()}\n"

        self.add_finding("4. EVIDENCE MESSAGE COVERAGE", evidence_summary)

    def explore_test_messages(self):
        """Explore messages.csv (test data to predict)"""
        messages = self.loader.messages

        # Basic stats
        summary = f"Total messages to predict: {len(messages)}\n\n"

        # Conversation type distribution
        conv_type_counts = messages['conversation_type'].value_counts()
        summary += "CONVERSATION TYPE DISTRIBUTION:\n\n"
        for conv_type, count in conv_type_counts.items():
            pct = count / len(messages) * 100
            summary += f"  {conv_type:12s}: {count:3d} ({pct:5.1f}%)\n"

        summary += "\n"

        # Media type distribution (inferred from message content)
        media_summary = self.analyze_media_types(messages)
        summary += "\n" + media_summary

        self.add_finding("5. TEST MESSAGES OVERVIEW", summary)

    def analyze_media_types(self, df: pd.DataFrame) -> str:
        """Analyze media types in messages"""
        # Handle different column naming between files
        text_col = 'message_text' if 'message_text' in df.columns else 'text'
        media_type_col = 'media_type' if 'media_type' in df.columns else None
        media_id_col = 'media_id' if 'media_id' in df.columns else None

        has_text = df[text_col].notna() & (df[text_col] != '')

        # Handle media_type/media_id vs individual image_id/voice_note_id columns
        if media_type_col and media_id_col:
            has_image = (df[media_type_col] == 'image') & df[media_id_col].notna()
            has_voice = (df[media_type_col] == 'voice') & df[media_id_col].notna()
        else:
            has_image = df['image_id'].notna() if 'image_id' in df.columns else pd.Series([False] * len(df))
            has_voice = df['voice_note_id'].notna() if 'voice_note_id' in df.columns else pd.Series([False] * len(df))

        text_only = has_text & ~has_image & ~has_voice
        image_only = has_image & ~has_text & ~has_voice
        voice_only = has_voice & ~has_text & ~has_image
        text_image = has_text & has_image
        text_voice = has_text & has_voice

        total = len(df)

        summary = "MEDIA TYPE DISTRIBUTION:\n\n"
        summary += f"  Text only:       {text_only.sum():3d} ({text_only.sum()/total*100:5.1f}%)\n"
        summary += f"  Image only:      {image_only.sum():3d} ({image_only.sum()/total*100:5.1f}%)\n"
        summary += f"  Voice only:      {voice_only.sum():3d} ({voice_only.sum()/total*100:5.1f}%)\n"
        summary += f"  Text + Image:    {text_image.sum():3d} ({text_image.sum()/total*100:5.1f}%)\n"
        summary += f"  Text + Voice:    {text_voice.sum():3d} ({text_voice.sum()/total*100:5.1f}%)\n"
        summary += f"\n"
        summary += f"  Total with text:  {has_text.sum():3d} ({has_text.sum()/total*100:5.1f}%)\n"
        summary += f"  Total with image: {has_image.sum():3d} ({has_image.sum()/total*100:5.1f}%)\n"
        summary += f"  Total with voice: {has_voice.sum():3d} ({has_voice.sum()/total*100:5.1f}%)\n"

        return summary

    def explore_users_groups_businesses(self):
        """Explore user, group, and business metadata"""
        users = self.loader.users
        groups = self.loader.groups
        businesses = self.loader.businesses

        summary = f"USER ACCOUNTS:\n"
        summary += f"  Total users: {len(users)}\n"
        if 'notification_preference' in users.columns:
            pref_counts = users['notification_preference'].value_counts()
            summary += f"\n  Notification preferences:\n"
            for pref, count in pref_counts.items():
                summary += f"    {pref}: {count}\n"

        summary += f"\n\nGROUPS:\n"
        summary += f"  Total groups: {len(groups)}\n"
        if 'group_type' in groups.columns:
            type_counts = groups['group_type'].value_counts()
            summary += f"\n  Group types:\n"
            for gtype, count in type_counts.items():
                summary += f"    {gtype}: {count}\n"

        summary += f"\n\nBUSINESS ACCOUNTS:\n"
        summary += f"  Total businesses: {len(businesses)}\n"
        if 'category' in businesses.columns:
            cat_counts = businesses['category'].value_counts()
            summary += f"\n  Top 10 business categories:\n"
            for cat, count in cat_counts.head(10).items():
                summary += f"    {cat}: {count}\n"

        self.add_finding("6. USERS, GROUPS, AND BUSINESSES", summary)

    def explore_message_history(self):
        """Explore message_history.csv"""
        history = self.loader.message_history

        summary = f"Total historical messages: {len(history)}\n\n"

        # Conversation type breakdown
        if 'conversation_type' in history.columns:
            conv_counts = history['conversation_type'].value_counts()
            summary += "Conversation type breakdown:\n"
            for conv_type, count in conv_counts.items():
                pct = count / len(history) * 100
                summary += f"  {conv_type}: {count} ({pct:.1f}%)\n"

        # Media types in history
        summary += "\n" + self.analyze_media_types(history)

        # Time span
        if 'timestamp' in history.columns:
            timestamps = pd.to_datetime(history['timestamp'])
            summary += f"\nTime span:\n"
            summary += f"  Earliest: {timestamps.min()}\n"
            summary += f"  Latest:   {timestamps.max()}\n"
            summary += f"  Duration: {(timestamps.max() - timestamps.min()).days} days\n"

        self.add_finding("7. MESSAGE HISTORY ANALYSIS", summary)

    def explore_message_events(self):
        """Explore message_events.csv (user reactions)"""
        events = self.loader.message_events

        summary = f"Total message events: {len(events)}\n\n"

        if 'event_type' in events.columns:
            event_counts = events['event_type'].value_counts()
            summary += "Event type distribution:\n"
            for event_type, count in event_counts.items():
                pct = count / len(events) * 100
                summary += f"  {event_type}: {count} ({pct:.1f}%)\n"

        # Unique messages with events
        unique_msgs = events['message_id'].nunique()
        summary += f"\nUnique messages with recorded events: {unique_msgs}\n"

        # Events per message
        events_per_msg = events.groupby('message_id').size()
        summary += f"\nEvents per message:\n"
        summary += f"  Mean:   {events_per_msg.mean():.2f}\n"
        summary += f"  Median: {events_per_msg.median():.0f}\n"
        summary += f"  Max:    {events_per_msg.max()}\n"

        self.add_finding("8. MESSAGE EVENTS (User Reactions)", summary)

    def explore_relationships(self):
        """Explore group_members and user_business_history"""
        group_members = self.loader.group_members
        user_biz_history = self.loader.user_business_history

        summary = "GROUP MEMBERSHIPS:\n"
        summary += f"  Total membership records: {len(group_members)}\n"
        summary += f"  Unique users in groups: {group_members['user_id'].nunique()}\n"
        summary += f"  Unique groups: {group_members['group_id'].nunique()}\n"

        members_per_group = group_members.groupby('group_id').size()
        summary += f"\n  Members per group:\n"
        summary += f"    Mean:   {members_per_group.mean():.1f}\n"
        summary += f"    Median: {members_per_group.median():.0f}\n"
        summary += f"    Min:    {members_per_group.min()}\n"
        summary += f"    Max:    {members_per_group.max()}\n"

        summary += "\n\nUSER-BUSINESS INTERACTIONS:\n"
        summary += f"  Total interaction records: {len(user_biz_history)}\n"
        summary += f"  Unique users: {user_biz_history['user_id'].nunique()}\n"
        summary += f"  Unique businesses: {user_biz_history['business_id'].nunique()}\n"

        if 'interaction_type' in user_biz_history.columns:
            interaction_counts = user_biz_history['interaction_type'].value_counts()
            summary += f"\n  Interaction types:\n"
            for itype, count in interaction_counts.items():
                summary += f"    {itype}: {count}\n"

        self.add_finding("9. RELATIONSHIPS (Groups & Business)", summary)

    def explore_media_files(self):
        """Explore images and voice notes metadata"""
        images = self.loader.images
        voice_notes = self.loader.voice_notes

        summary = f"IMAGES:\n"
        summary += f"  Total images: {len(images)}\n"
        if 'file_size_kb' in images.columns:
            summary += f"  Total size: {images['file_size_kb'].sum():.1f} KB\n"
            summary += f"  Avg size: {images['file_size_kb'].mean():.1f} KB\n"

        summary += f"\n\nVOICE NOTES:\n"
        summary += f"  Total voice notes: {len(voice_notes)}\n"
        if 'duration_seconds' in voice_notes.columns:
            summary += f"  Total duration: {voice_notes['duration_seconds'].sum():.1f} seconds\n"
            summary += f"  Avg duration: {voice_notes['duration_seconds'].mean():.1f} seconds\n"
        if 'file_size_kb' in voice_notes.columns:
            summary += f"  Total size: {voice_notes['file_size_kb'].sum():.1f} KB\n"

        self.add_finding("10. MEDIA FILES", summary)

    def check_data_quality(self):
        """Check for missing values and data quality issues"""
        summary = "DATA QUALITY CHECKS\n\n"

        datasets = {
            'messages.csv': self.loader.messages,
            'sample_messages.csv': self.loader.samples,
            'users.csv': self.loader.users,
            'groups.csv': self.loader.groups,
            'businesses.csv': self.loader.businesses,
            'message_history.csv': self.loader.message_history,
            'message_events.csv': self.loader.message_events,
        }

        for name, df in datasets.items():
            missing = df.isnull().sum()
            if missing.sum() > 0:
                summary += f"{name}:\n"
                for col, count in missing[missing > 0].items():
                    pct = count / len(df) * 100
                    summary += f"  {col}: {count} missing ({pct:.1f}%)\n"
                summary += "\n"
            else:
                summary += f"{name}: No missing values\n\n"

        self.add_finding("11. DATA QUALITY", summary)

    def explore_daily_summary(self):
        """Explore daily_notification_summary.csv"""
        daily = self.loader.daily_summary

        summary = f"Total daily summary records: {len(daily)}\n\n"

        if 'user_id' in daily.columns:
            summary += f"Unique users: {daily['user_id'].nunique()}\n"

        if 'date' in daily.columns:
            dates = pd.to_datetime(daily['date'])
            summary += f"\nDate range:\n"
            summary += f"  From: {dates.min()}\n"
            summary += f"  To:   {dates.max()}\n"
            summary += f"  Days: {(dates.max() - dates.min()).days + 1}\n"

        # Average notifications per user per day
        numeric_cols = daily.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            summary += f"\nAverage values:\n"
            for col in numeric_cols:
                if col != 'user_id':
                    summary += f"  {col}: {daily[col].mean():.2f}\n"

        self.add_finding("12. DAILY NOTIFICATION SUMMARY", summary)

    def generate_visualizations(self):
        """Generate visualization plots if matplotlib is available"""
        if not self.has_matplotlib:
            return

        print("\n" + "=" * 80)
        print("Generating visualizations...")
        print("=" * 80)

        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Message Notification Router - Data Exploration', fontsize=16)

        # Plot 1: Action distribution
        samples = self.loader.samples
        action_counts = samples['action'].value_counts()
        axes[0, 0].bar(action_counts.index, action_counts.values, color=['#2ecc71', '#3498db', '#e74c3c'])
        axes[0, 0].set_title('Action Distribution (Training Samples)')
        axes[0, 0].set_ylabel('Count')
        for i, v in enumerate(action_counts.values):
            axes[0, 0].text(i, v + 1, str(v), ha='center', fontweight='bold')

        # Plot 2: Confidence scores by action
        for action in ['notify', 'digest', 'mute']:
            action_samples = samples[samples['action'] == action]
            if len(action_samples) > 0:
                axes[0, 1].hist(action_samples['confidence'], alpha=0.6, label=action, bins=10)
        axes[0, 1].set_title('Confidence Score Distribution by Action')
        axes[0, 1].set_xlabel('Confidence')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].legend()

        # Plot 3: Conversation type distribution
        messages = self.loader.messages
        conv_counts = messages['conversation_type'].value_counts()
        axes[1, 0].barh(conv_counts.index, conv_counts.values, color='#9b59b6')
        axes[1, 0].set_title('Conversation Type Distribution (Test Set)')
        axes[1, 0].set_xlabel('Count')
        for i, v in enumerate(conv_counts.values):
            axes[1, 0].text(v + 2, i, str(v), va='center')

        # Plot 4: Media type distribution
        text_col = 'message_text' if 'message_text' in messages.columns else 'text'
        has_text = messages[text_col].notna() & (messages[text_col] != '')

        if 'media_type' in messages.columns and 'media_id' in messages.columns:
            has_image = (messages['media_type'] == 'image') & messages['media_id'].notna()
            has_voice = (messages['media_type'] == 'voice') & messages['media_id'].notna()
        else:
            has_image = messages['image_id'].notna() if 'image_id' in messages.columns else pd.Series([False] * len(messages))
            has_voice = messages['voice_note_id'].notna() if 'voice_note_id' in messages.columns else pd.Series([False] * len(messages))

        media_counts = {
            'Text only': (has_text & ~has_image & ~has_voice).sum(),
            'Image only': (has_image & ~has_text & ~has_voice).sum(),
            'Voice only': (has_voice & ~has_text & ~has_image).sum(),
            'Text+Image': (has_text & has_image).sum(),
            'Text+Voice': (has_text & has_voice).sum(),
        }

        axes[1, 1].pie(media_counts.values(), labels=media_counts.keys(), autopct='%1.1f%%', startangle=90)
        axes[1, 1].set_title('Media Type Distribution')

        plt.tight_layout()

        output_path = Path(__file__).parent / "exploration_plots.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"[+] Saved visualizations to: {output_path}")
        plt.close()

    def save_report(self):
        """Save findings to exploration_results.txt"""
        output_path = Path(__file__).parent / "exploration_results.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("MESSAGE NOTIFICATION ROUTER - DATA EXPLORATION REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {pd.Timestamp.now()}\n")
            f.write("=" * 80 + "\n")

            for finding in self.findings:
                f.write(finding)

            f.write("\n" + "=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")

        print("\n" + "=" * 80)
        print(f"[+] Report saved to: {output_path}")
        print("=" * 80)

    def run_full_exploration(self):
        """Run complete data exploration"""
        print("\nStarting comprehensive data exploration...\n")

        # Explore all datasets
        self.explore_samples()
        self.explore_test_messages()
        self.explore_users_groups_businesses()
        self.explore_message_history()
        self.explore_message_events()
        self.explore_relationships()
        self.explore_media_files()
        self.explore_daily_summary()
        self.check_data_quality()

        # Generate visualizations if possible
        self.generate_visualizations()

        # Save report
        self.save_report()

        print("\n" + "=" * 80)
        print("EXPLORATION COMPLETE")
        print("=" * 80)
        print("\nKey Takeaways:")
        print(f"  - {len(self.loader.samples)} training samples to learn from")
        print(f"  - {len(self.loader.messages)} test messages to predict")
        print(f"  - {len(self.loader.message_history)} historical messages for context")
        print(f"  - {len(self.loader.users)} users, {len(self.loader.groups)} groups, {len(self.loader.businesses)} businesses")
        print(f"  - Rich multimodal data: text, images ({len(self.loader.images)}), voice ({len(self.loader.voice_notes)})")
        print(f"  - User interaction events: {len(self.loader.message_events)} reactions tracked")
        print("\nNext steps:")
        print("  1. Review exploration_results.txt for detailed findings")
        if self.has_matplotlib:
            print("  2. Check exploration_plots.png for visual insights")
        print("  3. Design feature engineering strategy based on these insights")
        print("  4. Build prediction model considering action imbalance")
        print("=" * 80 + "\n")


def main():
    """Main execution function"""
    try:
        explorer = DataExplorer(dataset_path="../dataset")
        explorer.run_full_exploration()
        return 0
    except Exception as e:
        print(f"\n❌ Error during exploration: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
