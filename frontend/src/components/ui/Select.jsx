// components/ui/Select.jsx - Shadcn style Select
import React, { useState, useRef, useEffect } from "react";
import { useTheme } from "../ThemeProvider";
import { ChevronDown, Check, Search, X } from "lucide-react";
import { cn } from "../../utils/cn";
import Button from "./Button";
import Input from "./Input";

const Select = React.forwardRef((props, ref) => {
    const containerRef = useRef(null);
    const {
        className,
        options = [],
        value,
        defaultValue,
        placeholder = "Select an option",
        multiple = false,
        disabled = false,
        required = false,
        label,
        description,
        error,
        searchable = false,
        clearable = false,
        loading = false,
        id,
        name,
        onChange,
        onOpenChange,
        ...rest
    } = props;
    const { theme } = useTheme();
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");

    // Close dropdown when clicking outside
    useEffect(() => {
        if (!isOpen) return;
        function handleClickOutside(event) {
            if (containerRef.current && !containerRef.current.contains(event.target)) {
                setIsOpen(false);
                onOpenChange?.(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen, onOpenChange]);

    // Generate unique ID if not provided
    const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;

    // Filter options based on search
    const filteredOptions = searchable && searchTerm
        ? options.filter(option =>
            option.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (option.value && option.value.toString().toLowerCase().includes(searchTerm.toLowerCase()))
        )
        : options;

    // Get selected option(s) for display
    const getSelectedDisplay = () => {
        if (!value) return placeholder;

        if (multiple) {
            const selectedOptions = options.filter(opt => value.includes(opt.value));
            if (selectedOptions.length === 0) return placeholder;
            if (selectedOptions.length === 1) return selectedOptions[0].label;
            return `${selectedOptions.length} items selected`;
        }

        const selectedOption = options.find(opt => opt.value === value);
        return selectedOption ? selectedOption.label : placeholder;
    };

    const handleToggle = () => {
        if (!disabled) {
            const newIsOpen = !isOpen;
            setIsOpen(newIsOpen);
            onOpenChange?.(newIsOpen);
            if (!newIsOpen) {
                setSearchTerm("");
            }
        }
    };

    const handleOptionSelect = (option) => {
        if (multiple) {
            const newValue = value || [];
            const updatedValue = newValue.includes(option.value)
                ? newValue.filter(v => v !== option.value)
                : [...newValue, option.value];
            onChange?.(updatedValue);
        } else {
            onChange?.(option.value);
            setIsOpen(false);
            onOpenChange?.(false);
        }
    };

    const handleClear = (e) => {
        e.stopPropagation();
        onChange?.(multiple ? [] : '');
    };

    const handleSearchChange = (e) => {
        setSearchTerm(e.target.value);
    };

    const isSelected = (optionValue) => {
        if (multiple) {
            return value?.includes(optionValue) || false;
        }
        return value === optionValue;
    };

    const hasValue = multiple ? value?.length > 0 : value !== undefined && value !== '';

    return (
        <div ref={containerRef} className={cn("relative", className)}>
            {label && (
                <div className="flex items-center mb-1">
                    <label
                        htmlFor={selectId}
                        className={cn(
                            "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
                            error ? "text-destructive" : theme === 'dark' ? "text-[#e0e7ff]" : "text-foreground"
                        )}
                    >
                        {label}
                        {required && <span className="text-destructive ml-1">*</span>}
                    </label>
                </div>
            )}

            <div className="relative flex items-center gap-2">
                <button
                    ref={ref}
                    id={selectId}
                    type="button"
                    className={cn(
                        "relative flex h-10 w-full items-center flex-nowrap rounded-md border px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
                        theme === 'dark' ? "bg-[#23232a] text-[#e0e7ff] border-[#334155]" : "bg-white text-black border-input",
                        error && "border-destructive focus:ring-destructive",
                        !hasValue && (theme === 'dark' ? "text-[#94a3b8]" : "text-muted-foreground"),
                        "mt-0 gap-2"
                    )}
                    onClick={handleToggle}
                    disabled={disabled}
                    aria-expanded={isOpen}
                    aria-haspopup="listbox"
                    {...rest}
                >
                    <span className={cn("truncate text-left", theme === 'dark' ? "text-[#e0e7ff]" : "text-foreground")}>{getSelectedDisplay()}</span>
                    {loading && (
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                    )}
                    {clearable && hasValue && !loading && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-4 w-4 p-0"
                            onClick={handleClear}
                            tabIndex={-1}
                        >
                            <X className="h-3 w-3" />
                        </Button>
                    )}
                    <ChevronDown className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")} />
                </button>

                {/* Hidden native select for form submission */}
                <select
                    name={name}
                    value={multiple
                        ? Array.isArray(value) ? value : []
                        : (Array.isArray(value) ? (value[0] || '') : (value ?? ''))}
                    onChange={() => { }} // Controlled by our custom logic
                    className="sr-only"
                    tabIndex={-1}
                    multiple={multiple}
                    required={required}
                >
                    <option value="">Select...</option>
                    {options.map(option => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>

                {/* Dropdown */}
                {isOpen && (
                    <div className={cn("absolute left-0 z-50 w-full mt-1 border rounded-md shadow-md", theme === 'dark' ? "bg-[#23232a] text-[#e0e7ff] border-[#334155]" : "bg-white text-black border-border")}>
                        {searchable && (
                            <div className="p-2 border-b">
                                <div className="relative">
                                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        placeholder="Search options..."
                                        value={searchTerm}
                                        onChange={handleSearchChange}
                                        className="pl-8"
                                    />
                                </div>
                            </div>
                        )}

                        <div className="py-1 max-h-60 overflow-auto">
                            {filteredOptions.length === 0 ? (
                                <div className="px-3 py-2 text-sm text-muted-foreground">
                                    {searchTerm ? 'No options found' : 'No options available'}
                                </div>
                            ) : (
                                filteredOptions.map((option) => (
                                    <div
                                        key={option.value}
                                        className={cn(
                                            "relative flex cursor-pointer select-none items-center rounded-sm px-3 py-2 text-sm outline-none",
                                            theme === 'dark' ? "hover:bg-[#18181b] hover:text-[#7dd3fc]" : "hover:bg-accent hover:text-accent-foreground",
                                            isSelected(option.value) && (theme === 'dark' ? "bg-primary text-[#e0e7ff]" : "bg-primary text-primary-foreground"),
                                            option.disabled && "pointer-events-none opacity-50"
                                        )}
                                        onClick={() => !option.disabled && handleOptionSelect(option)}
                                    >
                                        <span className="flex-1">{option.label}</span>
                                        {multiple && isSelected(option.value) && (
                                            <Check className="h-4 w-4" />
                                        )}
                                        {option.description && (
                                            <span className="text-xs text-muted-foreground ml-2">
                                                {option.description}
                                            </span>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}
            </div>

            {description && !error && (
                <p className="text-sm text-muted-foreground mt-1">
                    {description}
                </p>
            )}

            {error && (
                <p className="text-sm text-destructive mt-1">
                    {error}
                </p>
            )}
        </div>
    );
});

Select.displayName = "Select";

export default Select;
