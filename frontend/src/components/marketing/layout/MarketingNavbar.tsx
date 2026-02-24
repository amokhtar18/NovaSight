/**
 * MarketingNavbar Component
 * 
 * Sticky navigation bar for marketing pages.
 * Features frosted glass effect on scroll and mobile hamburger menu.
 */

import * as React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Menu, X } from 'lucide-react';

const navLinks = [
  { label: 'Features', href: '/features' },
  { label: 'Solutions', href: '/solutions' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'About', href: '/about' },
];

export interface MarketingNavbarProps {
  /** Additional CSS classes */
  className?: string;
}

export function MarketingNavbar({ className }: MarketingNavbarProps) {
  const prefersReducedMotion = useReducedMotion();
  const [isScrolled, setIsScrolled] = React.useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const menuButtonRef = React.useRef<HTMLButtonElement>(null);
  const mobileMenuRef = React.useRef<HTMLDivElement>(null);

  // Handle scroll
  React.useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close menu on route change
  React.useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobileMenuOpen]);

  // Focus trap for mobile menu
  React.useEffect(() => {
    if (!isMobileMenuOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsMobileMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isMobileMenuOpen]);

  const mobileMenuVariants = {
    closed: {
      opacity: 0,
      y: -20,
    },
    open: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.2,
        staggerChildren: 0.05,
        delayChildren: 0.1,
      },
    },
    exit: {
      opacity: 0,
      y: -20,
      transition: { duration: 0.15 },
    },
  };

  const mobileItemVariants = {
    closed: { opacity: 0, x: -20 },
    open: { opacity: 1, x: 0 },
  };

  return (
    <>
      {/* Skip to content link */}
      <a
        href="#main-content"
        className={cn(
          'fixed left-4 top-4 z-[100] -translate-y-20 rounded-lg bg-accent-indigo px-4 py-2 text-white',
          'transition-transform focus:translate-y-0',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2'
        )}
      >
        Skip to content
      </a>

      <header
        className={cn(
          'fixed left-0 right-0 top-0 z-50',
          'h-16 md:h-[72px]',
          'transition-all duration-base',
          isScrolled
            ? 'border-b border-border/50 bg-bg-primary/80 backdrop-blur-glass'
            : 'bg-transparent',
          className
        )}
      >
        <nav
          className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8"
          aria-label="Main navigation"
        >
          {/* Logo */}
          <Link
            to="/"
            className="flex items-center gap-2 text-xl font-bold"
          >
            <img
              src="/mobius_strip.png"
              alt="NovaSight"
              className="h-8 w-auto object-contain"
            />
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              NovaSight
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden items-center gap-1 md:flex">
            {navLinks.map((link) => (
              <NavLink
                key={link.href}
                to={link.href}
                className={({ isActive }) =>
                  cn(
                    'rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'text-accent-indigo'
                      : 'text-muted-foreground hover:text-foreground'
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>

          {/* Desktop Actions */}
          <div className="hidden items-center gap-3 md:flex">
            <Button variant="ghost" asChild>
              <Link to="/login">Sign In</Link>
            </Button>
            <Button variant="gradient" className="shadow-glow-sm" asChild>
              <Link to="/register">Get Started</Link>
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            ref={menuButtonRef}
            type="button"
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-lg md:hidden',
              'text-foreground hover:bg-accent/10',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-expanded={isMobileMenuOpen}
            aria-controls="mobile-menu"
            aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {isMobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </nav>
      </header>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            id="mobile-menu"
            ref={mobileMenuRef}
            className={cn(
              'fixed inset-0 z-40 md:hidden',
              'bg-bg-primary/95 backdrop-blur-glass',
              'pt-20'
            )}
            initial="closed"
            animate="open"
            exit="exit"
            variants={prefersReducedMotion ? {} : mobileMenuVariants}
            role="dialog"
            aria-modal="true"
            aria-label="Mobile navigation menu"
          >
            <nav className="flex flex-col items-center gap-2 px-4 py-8">
              {navLinks.map((link) => (
                <motion.div
                  key={link.href}
                  variants={prefersReducedMotion ? {} : mobileItemVariants}
                >
                  <NavLink
                    to={link.href}
                    className={({ isActive }) =>
                      cn(
                        'block rounded-lg px-6 py-3 text-lg font-medium transition-colors',
                        isActive
                          ? 'text-accent-indigo'
                          : 'text-muted-foreground hover:text-foreground'
                      )
                    }
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {link.label}
                  </NavLink>
                </motion.div>
              ))}

              <motion.div
                className="mt-6 flex w-full flex-col gap-3 px-6"
                variants={prefersReducedMotion ? {} : mobileItemVariants}
              >
                <Button
                  variant="ghost"
                  className="w-full"
                  asChild
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <Link to="/login">Sign In</Link>
                </Button>
                <Button
                  variant="gradient"
                  className="w-full shadow-glow-sm"
                  asChild
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <Link to="/register">Get Started</Link>
                </Button>
              </motion.div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default MarketingNavbar;
