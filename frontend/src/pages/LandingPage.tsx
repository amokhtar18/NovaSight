/**
 * Landing Page - Welcome screen for authenticated users
 * 
 * Showcases the NovaSight design system with animated hero,
 * feature cards, and quick actions.
 */

import * as React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Database,
  GitBranch,
  BarChart3,
  Sparkles,
  Zap,
  Shield,
  ArrowRight,
  ChevronRight,
  Bot,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { GlassCard, GlassCardContent } from '@/components/ui/glass-card';
import { NeuralNetwork } from '@/components/backgrounds/NeuralNetwork';
import { fadeVariants, staggerContainerVariants, slideVariants } from '@/lib/motion-variants';
import { cn } from '@/lib/utils';

const features = [
  {
    title: 'Data Sources',
    description: 'Connect to any database, API, or file source with our unified connector framework.',
    icon: Database,
    color: 'text-accent-indigo',
    bgColor: 'bg-accent-indigo/10',
    href: '/app/datasources',
  },
  {
    title: 'Orchestration',
    description: 'Build, schedule, and monitor data pipelines with visual DAG builder.',
    icon: GitBranch,
    color: 'text-neon-green',
    bgColor: 'bg-neon-green/10',
    href: '/app/jobs',
  },
  {
    title: 'Analytics',
    description: 'Create interactive dashboards and explore your data with SQL editor.',
    icon: BarChart3,
    color: 'text-accent-purple',
    bgColor: 'bg-accent-purple/10',
    href: '/app/dashboards',
  },
  {
    title: 'AI Assistant',
    description: 'Ask questions in plain English and let AI generate SQL queries for you.',
    icon: Bot,
    color: 'text-neon-pink',
    bgColor: 'bg-neon-pink/10',
    href: '/app/query',
  },
];

const highlights = [
  {
    icon: Zap,
    title: 'Blazing Fast',
    description: 'Powered by ClickHouse for sub-second query performance',
  },
  {
    icon: Shield,
    title: 'Enterprise Security',
    description: 'Multi-tenant isolation with role-based access control',
  },
  {
    icon: Sparkles,
    title: 'AI-Powered',
    description: 'Natural language queries and intelligent insights',
  },
];

function FeatureCard({
  feature,
  index,
}: {
  feature: typeof features[0];
  index: number;
}) {
  return (
    <motion.div
      variants={fadeVariants}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
    >
      <Link to={feature.href}>
        <GlassCard variant="interactive" className="h-full">
          <GlassCardContent className="p-6">
            <div
              className={cn(
                'mb-4 flex h-12 w-12 items-center justify-center rounded-xl',
                feature.bgColor
              )}
            >
              <feature.icon className={cn('h-6 w-6', feature.color)} />
            </div>
            <h3 className="mb-2 text-lg font-semibold">{feature.title}</h3>
            <p className="mb-4 text-sm text-muted-foreground">{feature.description}</p>
            <div className="flex items-center text-sm font-medium text-accent-purple">
              Get Started
              <ChevronRight className="ml-1 h-4 w-4" />
            </div>
          </GlassCardContent>
        </GlassCard>
      </Link>
    </motion.div>
  );
}

export function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Animated Background */}
      <NeuralNetwork nodeCount={60} interactive speed={0.4} />

      {/* Gradient Overlays */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/4 top-1/4 h-[500px] w-[500px] rounded-full bg-accent-purple/20 blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 h-[400px] w-[400px] rounded-full bg-neon-cyan/15 blur-[100px]" />
      </div>

      {/* Content */}
      <div className="relative">
        {/* Hero Section */}
        <motion.section
          variants={staggerContainerVariants}
          initial="hidden"
          animate="visible"
          className="container mx-auto px-6 py-20 text-center"
        >
          {/* Badge */}
          <motion.div
            variants={fadeVariants}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-accent-purple/30 bg-accent-purple/10 px-4 py-2"
          >
            <Sparkles className="h-4 w-4 text-accent-purple" />
            <span className="text-sm font-medium">AI-Powered Data Platform</span>
          </motion.div>

          {/* Title */}
          <motion.h1
            variants={slideVariants}
            className="mb-6 text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl"
          >
            <span className="text-gradient">NovaSight</span>
            <br />
            <span className="text-muted-foreground">
              Your Data, Transformed
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            variants={fadeVariants}
            className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground"
          >
            Connect, transform, and visualize your data with our modern BI platform.
            Built for teams that demand performance, security, and simplicity.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            variants={fadeVariants}
            className="flex flex-wrap items-center justify-center gap-4"
          >
            <Button variant="gradient" size="lg" asChild>
              <Link to="/app/dashboard">
                Go to Dashboard
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link to="/app/docs">
                View Documentation
              </Link>
            </Button>
          </motion.div>
        </motion.section>

        {/* Features Grid */}
        <section className="container mx-auto px-6 py-16">
          <motion.div
            variants={staggerContainerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-100px' }}
            className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
          >
            {features.map((feature, index) => (
              <FeatureCard key={feature.title} feature={feature} index={index} />
            ))}
          </motion.div>
        </section>

        {/* Highlights Section */}
        <section className="container mx-auto px-6 py-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="rounded-2xl border border-border bg-bg-secondary/50 backdrop-blur-sm"
          >
            <div className="grid divide-y divide-border md:grid-cols-3 md:divide-x md:divide-y-0">
              {highlights.map((highlight, index) => (
                <motion.div
                  key={highlight.title}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-start gap-4 p-8"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-purple/20">
                    <highlight.icon className="h-5 w-5 text-accent-purple" />
                  </div>
                  <div>
                    <h3 className="mb-1 font-semibold">{highlight.title}</h3>
                    <p className="text-sm text-muted-foreground">
                      {highlight.description}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>

        {/* AI CTA Section */}
        <section className="container mx-auto px-6 py-16">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="relative overflow-hidden rounded-2xl border border-accent-purple/30 bg-gradient-to-br from-accent-purple/20 via-bg-secondary to-neon-pink/10 p-8 md:p-12"
          >
            {/* Decorative elements */}
            <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-accent-purple/30 blur-3xl" />
            <div className="absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-neon-pink/20 blur-3xl" />

            <div className="relative flex flex-col items-center text-center md:flex-row md:text-left">
              <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-purple/30 md:mb-0 md:mr-8">
                <Bot className="h-8 w-8 text-accent-purple" />
              </div>
              <div className="flex-1">
                <h2 className="mb-2 text-2xl font-bold">Ask AI Anything</h2>
                <p className="text-muted-foreground">
                  Our AI assistant understands your data schema and can help you write
                  complex queries, build dashboards, and discover insights.
                </p>
              </div>
              <div className="mt-6 md:ml-8 md:mt-0">
                <Button variant="ai" size="lg">
                  <Sparkles className="mr-2 h-5 w-5" />
                  Try AI Assistant
                </Button>
              </div>
            </div>
          </motion.div>
        </section>
      </div>
    </div>
  );
}

export default LandingPage;
