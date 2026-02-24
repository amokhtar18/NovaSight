/**
 * HeroVisual Component
 * 
 * Logo showcase with 3D tilt effects for hero section.
 * Uses TiltCard for interactive effects.
 */

import * as React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { TiltCard } from '@/components/marketing/effects';

export interface HeroVisualProps {
  /** Additional CSS classes */
  className?: string;
}

// Logo showcase component
function LogoShowcase() {
  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center overflow-hidden rounded-2xl">
      {/* Animated background gradient */}
      <motion.div
        className="absolute inset-0 opacity-30"
        style={{
          background: 'radial-gradient(ellipse at center, hsl(var(--color-accent-purple) / 0.3) 0%, transparent 70%)',
        }}
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.2, 0.4, 0.2],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
      
      {/* Logo with 3D hover effect */}
      <motion.img
        src="/mobius_strip.png"
        alt="NovaSight"
        className="relative z-10 h-auto w-2/3 max-w-md object-contain drop-shadow-2xl"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        whileHover={{ scale: 1.05 }}
        style={{
          filter: 'drop-shadow(0 0 30px hsl(var(--color-accent-purple) / 0.4))',
        }}
      />
      
      {/* Slogan */}
      <motion.p
        className="relative z-10 mt-6 text-center text-lg font-medium text-muted-foreground sm:text-xl md:text-2xl"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        <span className="bg-gradient-to-r from-accent-purple via-neon-cyan to-accent-indigo bg-clip-text text-transparent">
          Infinite Insights. Limitless Possibilities.
        </span>
      </motion.p>
      
      {/* Subtle particle effects */}
      <div className="pointer-events-none absolute inset-0">
        {[...Array(6)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute h-1 w-1 rounded-full bg-neon-cyan/60"
            style={{
              left: `${20 + Math.random() * 60}%`,
              top: `${20 + Math.random() * 60}%`,
            }}
            animate={{
              y: [0, -20, 0],
              opacity: [0.3, 0.8, 0.3],
            }}
            transition={{
              duration: 3 + i * 0.5,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: i * 0.3,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export function HeroVisual({ className }: HeroVisualProps) {
  return (
    <div className={cn('relative mx-auto w-full max-w-4xl', className)}>
      {/* Main logo card */}
      <TiltCard maxTilt={8} glare glareOpacity={0.1}>
        <div className="h-[280px] w-full sm:h-[320px] md:h-[380px]">
          <LogoShowcase />
        </div>
      </TiltCard>
    </div>
  );
}

export default HeroVisual;
