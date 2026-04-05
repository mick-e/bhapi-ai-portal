export { Button, getButtonStyles } from './Button';
export type { ButtonProps, ButtonVariant, ButtonSize } from './Button';

export { Card, cardStyles } from './Card';
export type { CardProps } from './Card';

export { Input, inputStyles } from './Input';
export type { InputProps } from './Input';

export { Badge, badgeColors } from './Badge';
export type { BadgeProps, BadgeVariant } from './Badge';

export { Toast, toastColors, getToastAutoDismissMs } from './Toast';
export type { ToastProps, ToastVariant } from './Toast';

export { Avatar, avatarSizes, getInitials } from './Avatar';
export type { AvatarProps, AvatarSize } from './Avatar';

export { BhapiLogo, logoSizes } from './BhapiLogo';
export type { BhapiLogoProps, LogoSize } from './BhapiLogo';

export { PostCard, postCardStyles } from './PostCard';
export type { PostCardProps, PostCardAuthor } from './PostCard';

export { CommentThread, commentThreadStyles } from './CommentThread';
export type { CommentThreadProps, CommentItem } from './CommentThread';

export { MessageBubble, messageBubbleStyles } from './MessageBubble';
export type { MessageBubbleProps } from './MessageBubble';

export { ContactRequest, contactRequestStyles, SearchResultCard } from './ContactRequest';
export type { ContactRequestProps, SearchResultCardProps } from './ContactRequest';

export { AgeTierGate, ageTierGateStyles, checkTierPermission, getFeatureDescription } from './AgeTierGate';
export type { AgeTierGateProps } from './AgeTierGate';

export { ReportDialog, reportDialogStyles, DEFAULT_REPORT_REASONS } from './ReportDialog';
export type { ReportDialogProps, ReportTargetType, ReportReasonValue, ReportReasonOption } from './ReportDialog';

export { ModerationNotice, moderationNoticeStyles } from './ModerationNotice';
export type { ModerationNoticeProps, ModerationState } from './ModerationNotice';

export { TrustedAdultButton, trustedAdultButtonStyles } from './TrustedAdultButton';
export type { TrustedAdultButtonProps } from './TrustedAdultButton';

export { RiskScoreCard, scoreColor, trendLabel, trendVariant, confidenceVariant } from './RiskScoreCard';
export type { RiskScoreCardProps, RiskTrend, RiskConfidence } from './RiskScoreCard';

export { CreativeToolbar, PRESET_COLORS, SIZE_PRESETS, creativeToolbarStyles } from './CreativeToolbar';
export type { CreativeToolbarProps, BrushSize } from './CreativeToolbar';

export { StickerGrid, STICKER_CATEGORIES, stickerGridStyles } from './StickerGrid';
export type { StickerGridProps, Sticker, StickerCategory } from './StickerGrid';

export { MotionProvider, useReducedMotion } from './MotionProvider';
export { ContrastProvider, useHighContrast } from './ContrastProvider';
export { FontProvider, useDyslexiaFont } from './FontProvider';

export { MobileEmptyState } from './MobileEmptyState';

export const UI_VERSION = '0.5.0';
