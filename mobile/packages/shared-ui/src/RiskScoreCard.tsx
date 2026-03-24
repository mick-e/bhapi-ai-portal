/**
 * RiskScoreCard — Shared UI component
 *
 * Displays an AI safety risk score (0–100) with:
 *   - Circular score indicator (green 0-30, amber 31-60, red 61-100)
 *   - Trend arrow (up / down / stable)
 *   - Confidence badge
 *   - Top contributing factors list (max 3)
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Badge } from './Badge';

export type RiskTrend = 'up' | 'down' | 'stable';
export type RiskConfidence = 'low' | 'medium' | 'high';

export interface RiskScoreCardProps {
  score: number;
  trend: RiskTrend;
  confidence: RiskConfidence;
  factors: string[];
  accessibilityLabel?: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function scoreColor(score: number): string {
  if (score <= 30) return colors.semantic.success;
  if (score <= 60) return colors.semantic.warning;
  return colors.semantic.error;
}

function trendLabel(trend: RiskTrend): string {
  if (trend === 'up') return '↑ Rising';
  if (trend === 'down') return '↓ Falling';
  return '→ Stable';
}

function trendVariant(trend: RiskTrend): 'error' | 'success' | 'info' {
  if (trend === 'up') return 'error';
  if (trend === 'down') return 'success';
  return 'info';
}

function confidenceVariant(confidence: RiskConfidence): 'error' | 'warning' | 'success' {
  if (confidence === 'low') return 'error';
  if (confidence === 'medium') return 'warning';
  return 'success';
}

// ─── Component ────────────────────────────────────────────────────────────────

export function RiskScoreCard({
  score,
  trend,
  confidence,
  factors,
  accessibilityLabel,
}: RiskScoreCardProps) {
  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));
  const ringColor = scoreColor(clampedScore);
  const topFactors = factors.slice(0, 3);

  return React.createElement(
    View,
    {
      style: styles.container,
      accessibilityLabel: accessibilityLabel ?? `Risk score: ${clampedScore} out of 100`,
    },
    // Header row: circle + badges
    React.createElement(
      View,
      { style: styles.headerRow },
      // Score circle
      React.createElement(
        View,
        {
          style: [styles.circle, { borderColor: ringColor }],
          accessibilityLabel: `Score: ${clampedScore}`,
        },
        React.createElement(
          Text,
          { style: [styles.scoreText, { color: ringColor }] },
          String(clampedScore)
        ),
        React.createElement(
          Text,
          { style: styles.scoreLabel },
          '/100'
        )
      ),
      // Badges column
      React.createElement(
        View,
        { style: styles.badgeColumn },
        React.createElement(Badge, {
          text: trendLabel(trend),
          variant: trendVariant(trend),
          accessibilityLabel: `Trend: ${trend}`,
        }),
        React.createElement(View, { style: { height: spacing.xs } }),
        React.createElement(Badge, {
          text: `${confidence.charAt(0).toUpperCase() + confidence.slice(1)} confidence`,
          variant: confidenceVariant(confidence),
          accessibilityLabel: `Confidence: ${confidence}`,
        })
      )
    ),
    // Contributing factors
    topFactors.length > 0
      ? React.createElement(
          View,
          { style: styles.factorsContainer, accessibilityLabel: 'Contributing factors' },
          React.createElement(
            Text,
            { style: styles.factorsTitle },
            'Top Factors'
          ),
          ...topFactors.map((factor, index) =>
            React.createElement(
              View,
              { key: String(index), style: styles.factorRow },
              React.createElement(
                Text,
                { style: styles.factorBullet },
                '•'
              ),
              React.createElement(
                Text,
                { style: styles.factorText, numberOfLines: 2 },
                factor
              )
            )
          )
        )
      : null
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    padding: spacing.md,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  circle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 4,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
    backgroundColor: '#FFFFFF',
  },
  scoreText: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    fontFamily: typography.fontFamily,
    lineHeight: 28,
  },
  scoreLabel: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
  },
  badgeColumn: {
    flex: 1,
    alignItems: 'flex-start',
  },
  factorsContainer: {
    borderTopWidth: 1,
    borderTopColor: colors.neutral[200],
    paddingTop: spacing.sm,
  },
  factorsTitle: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[700],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  factorRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 4,
  },
  factorBullet: {
    color: colors.primary[500],
    marginRight: 6,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
  },
  factorText: {
    flex: 1,
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
    lineHeight: 18,
  },
});

export { scoreColor, trendLabel, trendVariant, confidenceVariant };
