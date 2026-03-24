import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';

interface Option {
  value: string;
  label: string;
  group?: string; // optional group label
}

interface CustomSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  disabled?: boolean;
  placeholder?: string;
  icon?: React.ReactNode;
  className?: string;
}

export const CustomSelect: React.FC<CustomSelectProps> = ({
  value,
  onChange,
  options,
  disabled = false,
  placeholder = 'Select...',
  icon,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const selectedOption = options.find(opt => opt.value === value);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Group options by group label if provided
  const groupedOptions = options.reduce<Record<string, Option[]>>((acc, opt) => {
    const group = opt.group || '';
    if (!acc[group]) acc[group] = [];
    acc[group].push(opt);
    return acc;
  }, {});

  const handleSelect = (optionValue: string) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className="w-full pl-11 pr-10 py-3.5 bg-surface border border-border-main rounded-xl text-sm font-bold text-text-primary focus:border-primary-start outline-none transition-all appearance-none cursor-pointer disabled:opacity-50 flex items-center justify-between"
      >
        <span className="flex items-center gap-2 truncate">
          {icon && <span className="text-primary-start opacity-70">{icon}</span>}
          <span className="truncate">{selectedOption?.label || placeholder}</span>
        </span>
        <ChevronDown className={`h-4 w-4 text-text-muted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && !disabled && (
        <div
          className="absolute z-[9999] mt-1 w-full bg-card border border-border-main rounded-xl shadow-xl max-h-60 overflow-y-auto custom-scrollbar"
          style={{ backgroundColor: 'var(--bg-card)' }}
        >
          {Object.entries(groupedOptions).map(([group, opts]) => (
            <div key={group}>
              {group && (
                <div className="px-4 py-1 text-xs font-black uppercase tracking-widest text-text-muted bg-surface/50 sticky top-0">
                  {group}
                </div>
              )}
              {opts.map((opt) => (
                <div
                  key={opt.value}
                  onClick={() => handleSelect(opt.value)}
                  className={`px-4 py-2 hover:bg-hover cursor-pointer text-sm font-bold text-text-primary ${group ? 'pl-6' : ''}`}
                >
                  {opt.label}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};