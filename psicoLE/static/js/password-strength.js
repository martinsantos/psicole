/**
 * Password Strength Meter
 * Provides visual feedback on password strength
 */

document.addEventListener('DOMContentLoaded', function() {
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const strengthMeter = document.getElementById('password-strength-meter');
    const strengthText = document.getElementById('password-strength-text');
    
    if (!passwordInput) return;

    // Password strength levels
    const strengthLevels = [
        { text: 'Muy débil', color: '#dc3545', minScore: 0 },
        { text: 'Débil', color: '#fd7e14', minScore: 2 },
        { text: 'Moderada', color: '#ffc107', minScore: 3 },
        { text: 'Fuerte', color: '#20c997', minScore: 4 },
        { text: 'Muy fuerte', color: '#198754', minScore: 5 }
    ];

    // Check password strength
    function checkPasswordStrength(password) {
        let score = 0;
        
        // Length check
        if (password.length >= 8) score++;
        if (password.length >= 12) score++;
        
        // Complexity checks
        if (/[A-Z]/.test(password)) score++; // Has uppercase
        if (/[a-z]/.test(password)) score++; // Has lowercase
        if (/[0-9]/.test(password)) score++; // Has number
        if (/[^A-Za-z0-9]/.test(password)) score++; // Has special char
        
        return Math.min(score, 5); // Cap at 5 for our levels
    }

    // Update strength meter
    function updateStrengthMeter(password) {
        if (!strengthMeter || !strengthText) return;
        
        if (password.length === 0) {
            strengthMeter.style.width = '0%';
            strengthMeter.className = 'progress-bar';
            strengthText.textContent = '';
            return;
        }
        
        const score = checkPasswordStrength(password);
        const level = strengthLevels.find(level => score <= level.minScore) || strengthLevels[strengthLevels.length - 1];
        const percentage = (score / 5) * 100;
        
        strengthMeter.style.width = `${percentage}%`;
        strengthMeter.className = 'progress-bar';
        strengthMeter.classList.add(`bg-${level.color}`);
        strengthText.textContent = level.text;
        strengthText.style.color = level.color;
    }

    // Check password match
    function checkPasswordMatch() {
        if (!confirmPasswordInput) return;
        
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        if (confirmPassword === '') return;
        
        if (password !== confirmPassword) {
            confirmPasswordInput.setCustomValidity('Las contraseñas no coinciden');
        } else {
            confirmPasswordInput.setCustomValidity('');
        }
    }

    // Event listeners
    passwordInput.addEventListener('input', function() {
        updateStrengthMeter(this.value);
        if (confirmPasswordInput && confirmPasswordInput.value) {
            checkPasswordMatch();
        }
    });

    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', checkPasswordMatch);
    }

    // Initialize
    updateStrengthMeter('');
});
