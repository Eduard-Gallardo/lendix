// Inicio de sesion

// Funcionalidad básica para el formulario
document.querySelector('form').addEventListener('submit', function(e) {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const button = document.querySelector('button[type="submit"]');
            
    if(email && password) {
    // Mostrar estado de carga
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Iniciando sesión...';
        button.disabled = true;
    }
});

// Rellenar automáticamente si hay datos en sessionStorage (opcional)
document.addEventListener('DOMContentLoaded', function() {
    const savedEmail = sessionStorage.getItem('rememberedEmail');
    if (savedEmail) {
        document.getElementById('email').value = savedEmail;
        document.getElementById('remember-me').checked = true;
    }
});

// Guardar email si "Recordarme" está marcado
document.getElementById('remember-me').addEventListener('change', function() {
    const email = document.getElementById('email').value;
    if (this.checked && email) {
        sessionStorage.setItem('rememberedEmail', email);
    } else {
        sessionStorage.removeItem('rememberedEmail');
    }
});

// Registro

// Validación en tiempo real
document.getElementById('email').addEventListener('blur', function() {
    const email = this.value;
    const validationDiv = document.getElementById('email-validation');
            
    if (!email) return;
            
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        validationDiv.querySelector('span').textContent = 'Por favor, ingrese un correo electrónico válido';
        validationDiv.classList.remove('hidden');
        this.classList.add('border-red-500');
    } else {
    // Verificar disponibilidad del email
    fetch('/registro/api/verificar-email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email })
        })
    .then(response => response.json())
    .then(data => {
        if (data.disponible) {
            validationDiv.classList.add('hidden');
            this.classList.remove('border-red-500');
        } else {
            validationDiv.querySelector('span').textContent = data.mensaje;
            validationDiv.classList.remove('hidden');
            this.classList.add('border-red-500');
        }
        });
        }
});

document.getElementById('telefono').addEventListener('blur', function() {
    const telefono = this.value;
    const validationDiv = document.getElementById('telefono-validation');
            
    if (!telefono) return;
            
    if (telefono.length < 10) {
        validationDiv.querySelector('span').textContent = 'El teléfono debe tener al menos 10 caracteres';
        validationDiv.classList.remove('hidden');
        this.classList.add('border-red-500');
    } else {
    // Verificar disponibilidad del teléfono
    fetch('/registro/api/verificar-telefono', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ telefono: telefono })
    })
    .then(response => response.json())
    .then(data => {
    if (data.disponible) {
        validationDiv.classList.add('hidden');
        this.classList.remove('border-red-500');
    } else {
        validationDiv.querySelector('span').textContent = data.mensaje;
        validationDiv.classList.remove('hidden');
        this.classList.add('border-red-500');
            }
        });
    }
});

document.getElementById('password').addEventListener('input', function() {
    const password = this.value;
    const validationDiv = document.getElementById('password-validation');
    const strengthBars = [
        document.getElementById('strength-1'),
        document.getElementById('strength-2'),
        document.getElementById('strength-3'),
        document.getElementById('strength-4')
    ];
            
    // Resetear todas las barras
    strengthBars.forEach(bar => {
        bar.classList.remove('bg-red-500', 'bg-yellow-500', 'bg-green-500');
        bar.classList.add('bg-gray-200');
    });
            
    if (password.length === 0) {
        validationDiv.classList.add('hidden');
        return;
    }
            
    // Validar longitud mínima
    if (password.length < 8) {
        validationDiv.classList.remove('hidden');
    } else {
        validationDiv.classList.add('hidden');
        }
            
// Calcular fortaleza
let strength = 0;
    if (password.length >= 6) strength++;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
            
// Aplicar colores según la fortaleza
for (let i = 0; i < Math.min(strength, 4); i++) {
    if (strength <= 2) {
        strengthBars[i].classList.add('bg-red-500');
    } else if (strength === 3) {
        strengthBars[i].classList.add('bg-yellow-500');
    } else {
        strengthBars[i].classList.add('bg-green-500');
    }
        strengthBars[i].classList.remove('bg-gray-200');
    }
});

document.getElementById('confirm-password').addEventListener('input', function() {
    const password = document.getElementById('password').value;
    const confirmPassword = this.value;
    const validationDiv = document.getElementById('confirm-validation');
            
    if (password !== confirmPassword) {
        validationDiv.classList.remove('hidden');
        this.classList.add('border-red-500');
    } else {
        validationDiv.classList.add('hidden');
        this.classList.remove('border-red-500');
    }
});

// Evitar envío del formulario si hay errores
document.querySelector('form').addEventListener('submit', function(e) {
    let hasErrors = false;

// Verificar validaciones
    const inputs = ['email', 'telefono', 'password', 'confirm-password'];
    inputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        const validationDiv = document.getElementById(`${inputId}-validation`);
                
    if (validationDiv && !validationDiv.classList.contains('hidden')) {
        hasErrors = true;
        input.focus();
    }
});
            
    if (hasErrors) {
        e.preventDefault();
        alert('Por favor, corrija los errores en el formulario antes de enviar.');
    }
});