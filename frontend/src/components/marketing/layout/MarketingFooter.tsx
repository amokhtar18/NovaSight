/**
 * MarketingFooter Component
 * 
 * Footer for marketing pages with newsletter signup, links, and social icons.
 */

import * as React from 'react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { NewsletterForm } from '../shared/NewsletterForm';
import { Github, Twitter, Linkedin, MessageCircle } from 'lucide-react';

const footerLinks = {
  product: {
    title: 'Product',
    links: [
      { label: 'Features', href: '/features' },
      { label: 'Pricing', href: '/pricing' },
      { label: 'Integrations', href: '/integrations' },
      { label: 'Changelog', href: '/changelog' },
      { label: 'Roadmap', href: '/roadmap' },
    ],
  },
  solutions: {
    title: 'Solutions',
    links: [
      { label: 'For Startups', href: '/solutions/startups' },
      { label: 'For Enterprise', href: '/solutions/enterprise' },
      { label: 'For Data Teams', href: '/solutions/data-teams' },
      { label: 'For Analytics', href: '/solutions/analytics' },
    ],
  },
  company: {
    title: 'Company',
    links: [
      { label: 'About', href: '/about' },
      { label: 'Blog', href: '/blog' },
      { label: 'Careers', href: '/careers' },
      { label: 'Contact', href: '/contact' },
      { label: 'Press', href: '/press' },
    ],
  },
  resources: {
    title: 'Resources',
    links: [
      { label: 'Documentation', href: '/docs' },
      { label: 'API Reference', href: '/docs/api' },
      { label: 'Community', href: '/community' },
      { label: 'Support', href: '/support' },
      { label: 'Status', href: '/status' },
    ],
  },
};

const socialLinks = [
  { label: 'Twitter', href: 'https://twitter.com/novasight', icon: Twitter },
  { label: 'GitHub', href: 'https://github.com/novasight', icon: Github },
  { label: 'LinkedIn', href: 'https://linkedin.com/company/novasight', icon: Linkedin },
  { label: 'Discord', href: 'https://discord.gg/novasight', icon: MessageCircle },
];

export interface MarketingFooterProps {
  /** Additional CSS classes */
  className?: string;
}

export function MarketingFooter({ className }: MarketingFooterProps) {
  const currentYear = new Date().getFullYear();

  return (
    <footer
      className={cn(
        'border-t border-border bg-bg-secondary',
        className
      )}
      aria-labelledby="footer-heading"
    >
      <h2 id="footer-heading" className="sr-only">
        Footer
      </h2>

      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
        {/* Top Section */}
        <div className="xl:grid xl:grid-cols-3 xl:gap-8">
          {/* Brand & Newsletter */}
          <div className="space-y-8 xl:col-span-1">
            <Link to="/" className="inline-block">
              <span className="flex items-center gap-2 text-2xl font-bold">
                <img
                  src="/mobius_strip.png"
                  alt="NovaSight"
                  className="h-8 w-auto object-contain"
                />
                <span className="bg-gradient-primary bg-clip-text text-transparent">
                  NovaSight
                </span>
              </span>
            </Link>
            <p className="max-w-xs text-sm text-muted-foreground">
              Transform your data into actionable insights with AI-powered analytics
              and seamless data orchestration.
            </p>
            <div className="max-w-sm">
              <h3 className="mb-3 text-sm font-semibold text-foreground">
                Subscribe to our newsletter
              </h3>
              <NewsletterForm
                variant="inline"
                placeholder="Your email"
                buttonText="Subscribe"
              />
            </div>
          </div>

          {/* Links Grid */}
          <div className="mt-16 grid grid-cols-2 gap-8 xl:col-span-2 xl:mt-0">
            <div className="md:grid md:grid-cols-2 md:gap-8">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  {footerLinks.product.title}
                </h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.product.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        to={link.href}
                        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-10 md:mt-0">
                <h3 className="text-sm font-semibold text-foreground">
                  {footerLinks.solutions.title}
                </h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.solutions.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        to={link.href}
                        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="md:grid md:grid-cols-2 md:gap-8">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  {footerLinks.company.title}
                </h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.company.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        to={link.href}
                        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-10 md:mt-0">
                <h3 className="text-sm font-semibold text-foreground">
                  {footerLinks.resources.title}
                </h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.resources.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        to={link.href}
                        className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="mt-12 border-t border-border pt-8">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            {/* Copyright */}
            <p className="text-sm text-muted-foreground">
              &copy; {currentYear} NovaSight, Inc. All rights reserved.
            </p>

            {/* Social Links */}
            <div className="flex items-center gap-4">
              {socialLinks.map((social) => (
                <a
                  key={social.label}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={cn(
                    'flex h-10 w-10 items-center justify-center rounded-full',
                    'text-muted-foreground transition-colors',
                    'hover:bg-accent/10 hover:text-foreground',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                  )}
                  aria-label={social.label}
                >
                  <social.icon className="h-5 w-5" />
                </a>
              ))}
            </div>

            {/* Legal Links */}
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <Link
                to="/privacy"
                className="transition-colors hover:text-foreground"
              >
                Privacy Policy
              </Link>
              <span className="hidden sm:inline">·</span>
              <Link
                to="/terms"
                className="transition-colors hover:text-foreground"
              >
                Terms of Service
              </Link>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default MarketingFooter;
