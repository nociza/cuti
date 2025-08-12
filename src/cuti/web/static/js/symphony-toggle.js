/**
 * Symphony Mode Toggle - Enhanced Interactive Component
 * Provides smooth animations and state management for the Symphony Mode toggle
 */

class SymphonyToggle {
    constructor(element) {
        this.element = element;
        this.checkbox = element.querySelector('input[type="checkbox"]');
        this.track = element.querySelector('.symphony-toggle-track');
        this.isAnimating = false;
        this.particles = [];
        
        this.init();
    }
    
    init() {
        // Create particle effects
        this.createParticles();
        
        // Bind events
        this.bindEvents();
        
        // Initialize state
        this.updateState(this.checkbox.checked);
        
        // Add sound effects (optional)
        this.initSoundEffects();
    }
    
    createParticles() {
        const particleContainer = document.createElement('div');
        particleContainer.className = 'symphony-particles';
        
        // Create 5 particles for animation
        for (let i = 0; i < 5; i++) {
            const particle = document.createElement('span');
            particle.className = 'particle';
            particleContainer.appendChild(particle);
            this.particles.push(particle);
        }
        
        this.track.appendChild(particleContainer);
    }
    
    bindEvents() {
        // Checkbox change event
        this.checkbox.addEventListener('change', (e) => {
            this.handleToggle(e.target.checked);
        });
        
        // Keyboard accessibility
        this.element.addEventListener('keydown', (e) => {
            if (e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                this.checkbox.checked = !this.checkbox.checked;
                this.handleToggle(this.checkbox.checked);
            }
        });
        
        // Hover effects
        this.element.addEventListener('mouseenter', () => {
            this.addHoverEffect();
        });
        
        this.element.addEventListener('mouseleave', () => {
            this.removeHoverEffect();
        });
    }
    
    handleToggle(isChecked) {
        if (this.isAnimating) return;
        
        this.isAnimating = true;
        
        // Add transition class
        this.element.classList.add('transitioning');
        
        // Update state
        this.updateState(isChecked);
        
        // Trigger animation
        this.animateToggle(isChecked);
        
        // Play sound effect
        this.playToggleSound(isChecked);
        
        // Dispatch custom event
        this.dispatchToggleEvent(isChecked);
        
        // Reset animation flag
        setTimeout(() => {
            this.isAnimating = false;
            this.element.classList.remove('transitioning');
        }, 600);
    }
    
    updateState(isChecked) {
        if (isChecked) {
            this.element.classList.add('symphony-active');
            this.element.setAttribute('aria-label', 'Symphony Mode: Active - Multiple agents orchestrated');
            this.startParticleAnimation();
            this.addGlowEffect();
        } else {
            this.element.classList.remove('symphony-active');
            this.element.setAttribute('aria-label', 'Solo Mode: Active - Single agent operation');
            this.stopParticleAnimation();
            this.removeGlowEffect();
        }
    }
    
    animateToggle(isChecked) {
        // Create ripple effect
        const ripple = document.createElement('div');
        ripple.className = 'toggle-ripple';
        ripple.style.cssText = `
            position: absolute;
            top: 50%;
            left: ${isChecked ? '75%' : '25%'};
            transform: translate(-50%, -50%);
            width: 20px;
            height: 20px;
            background: ${isChecked ? 'rgba(102, 126, 234, 0.6)' : 'rgba(255, 255, 255, 0.3)'};
            border-radius: 50%;
            pointer-events: none;
            animation: rippleExpand 0.6s ease-out forwards;
        `;
        
        this.track.appendChild(ripple);
        
        // Remove ripple after animation
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }
    
    startParticleAnimation() {
        this.particles.forEach((particle, index) => {
            setTimeout(() => {
                particle.style.animation = `particleFloat 3s linear infinite`;
                particle.style.animationDelay = `${index * 0.6}s`;
            }, index * 100);
        });
    }
    
    stopParticleAnimation() {
        this.particles.forEach(particle => {
            particle.style.animation = 'none';
        });
    }
    
    addGlowEffect() {
        const glow = document.createElement('div');
        glow.className = 'symphony-glow-effect';
        glow.style.cssText = `
            position: absolute;
            top: -20px;
            left: -20px;
            right: -20px;
            bottom: -20px;
            background: radial-gradient(circle, rgba(102, 126, 234, 0.2) 0%, transparent 70%);
            pointer-events: none;
            opacity: 0;
            animation: glowFadeIn 0.6s ease-out forwards;
            border-radius: 34px;
        `;
        
        this.element.appendChild(glow);
        this.glowEffect = glow;
    }
    
    removeGlowEffect() {
        if (this.glowEffect) {
            this.glowEffect.style.animation = 'glowFadeOut 0.6s ease-out forwards';
            setTimeout(() => {
                this.glowEffect.remove();
                this.glowEffect = null;
            }, 600);
        }
    }
    
    addHoverEffect() {
        this.element.classList.add('hovering');
        
        // Add magnetic effect
        this.element.addEventListener('mousemove', this.handleMouseMove);
    }
    
    removeHoverEffect() {
        this.element.classList.remove('hovering');
        this.element.removeEventListener('mousemove', this.handleMouseMove);
        
        // Reset transform
        const knob = this.track.querySelector('.symphony-toggle-knob');
        if (knob) {
            knob.style.transform = this.checkbox.checked ? 'translateX(112px)' : 'translateX(0)';
        }
    }
    
    handleMouseMove = (e) => {
        const rect = this.element.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const centerX = rect.width / 2;
        const deltaX = (x - centerX) / rect.width;
        
        const knob = this.track.querySelector('.symphony-toggle-knob');
        if (knob && !this.isAnimating) {
            const baseTransform = this.checkbox.checked ? 112 : 0;
            const magneticOffset = deltaX * 5; // 5px max magnetic effect
            knob.style.transform = `translateX(${baseTransform + magneticOffset}px)`;
        }
    }
    
    initSoundEffects() {
        // Create audio context for sound effects (optional)
        this.audioContext = null;
        
        // Initialize on first user interaction
        document.addEventListener('click', () => {
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
        }, { once: true });
    }
    
    playToggleSound(isChecked) {
        if (!this.audioContext) return;
        
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        // Different frequencies for on/off
        oscillator.frequency.value = isChecked ? 880 : 440; // A5 for on, A4 for off
        oscillator.type = 'sine';
        
        // Envelope
        gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.1, this.audioContext.currentTime + 0.01);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.1);
        
        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + 0.1);
    }
    
    dispatchToggleEvent(isChecked) {
        const event = new CustomEvent('symphonyModeChanged', {
            detail: {
                enabled: isChecked,
                mode: isChecked ? 'symphony' : 'solo',
                timestamp: Date.now()
            },
            bubbles: true
        });
        
        this.element.dispatchEvent(event);
    }
    
    // Public methods
    setEnabled(enabled) {
        if (this.checkbox.checked !== enabled) {
            this.checkbox.checked = enabled;
            this.handleToggle(enabled);
        }
    }
    
    getState() {
        return {
            enabled: this.checkbox.checked,
            mode: this.checkbox.checked ? 'symphony' : 'solo'
        };
    }
    
    setLoading(isLoading) {
        if (isLoading) {
            this.element.classList.add('symphony-toggle-loading');
            this.checkbox.disabled = true;
        } else {
            this.element.classList.remove('symphony-toggle-loading');
            this.checkbox.disabled = false;
        }
    }
}

// Add CSS animations dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes rippleExpand {
        to {
            width: 200px;
            height: 200px;
            opacity: 0;
        }
    }
    
    @keyframes glowFadeIn {
        to {
            opacity: 1;
        }
    }
    
    @keyframes glowFadeOut {
        to {
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    const toggles = document.querySelectorAll('.symphony-toggle-enhanced');
    toggles.forEach(toggle => {
        new SymphonyToggle(toggle);
    });
});

// Export for use in other modules
window.SymphonyToggle = SymphonyToggle;