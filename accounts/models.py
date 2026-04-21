"""
Accounts Models - Custom User and Role Management
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group


class UserManager(BaseUserManager):
    """Custom user manager."""
    
    def create_user(self, username, email=None, password=None, **extra_fields):
        """Create and save a regular user."""
        if not username:
            raise ValueError('El nombre de usuario es obligatorio')
        
        email = self.normalize_email(email) if email else None
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_admin') is not True:
            raise ValueError('Superuser must have is_admin=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User Model for CHE GOLOSO."""
    
    username = models.CharField(
        'Nombre de usuario',
        max_length=150,
        unique=True,
        help_text='Requerido. 150 caracteres o menos.'
    )
    email = models.EmailField(
        'Email',
        blank=True,
        null=True
    )
    first_name = models.CharField(
        'Nombre',
        max_length=150,
        blank=True
    )
    last_name = models.CharField(
        'Apellido',
        max_length=150,
        blank=True
    )
    
    # Status fields
    is_active = models.BooleanField(
        'Activo',
        default=True,
        help_text='Indica si el usuario puede acceder al sistema.'
    )
    is_admin = models.BooleanField(
        'Es administrador',
        default=False,
        help_text='Indica si el usuario tiene acceso completo.'
    )
    is_staff = models.BooleanField(
        'Es staff',
        default=False,
        help_text='Indica si el usuario puede acceder al admin de Django.'
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        'Fecha de registro',
        auto_now_add=True
    )
    last_login = models.DateTimeField(
        'Último acceso',
        blank=True,
        null=True
    )
    updated_at = models.DateTimeField(
        'Última actualización',
        auto_now=True
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.username
    
    def get_full_name(self):
        """Return the full name of the user."""
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name or self.username
    
    def get_short_name(self):
        """Return the short name of the user."""
        return self.first_name or self.username
    
    @property
    def role_names(self):
        """Return list of role names."""
        return list(self.groups.values_list('name', flat=True))
    
    def has_role(self, role_name):
        """Check if user has a specific role."""
        return self.groups.filter(name=role_name).exists()
    
    def is_cashier(self):
        """Check if user is a cashier."""
        return self.has_role('Cashier') or self.has_role('Cajero Manager') or self.has_role('Admin') or self.is_superuser
    
    def is_cajero_manager(self):
        """Check if user is a cajero manager."""
        return self.has_role('Cajero Manager') or self.has_role('Admin') or self.is_superuser
    
    def is_manager(self):
        """Check if user is a manager (admin or cajero manager)."""
        return self.has_role('Admin') or self.has_role('Cajero Manager') or self.is_superuser
    
    def is_stock_manager(self):
        """Check if user has stock access."""
        return self.has_role('Cajero Manager') or self.has_role('Admin') or self.is_superuser


class Role(Group):
    """
    Proxy model for Django's Group to add extra functionality.
    Roles: Admin, Cajero Manager, Cashier
    """
    
    class Meta:
        proxy = True
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
    
    ROLE_CHOICES = [
        ('Admin', 'Administrador'),
        ('Cajero Manager', 'Cajero Manager'),
        ('Cashier', 'Cajero'),
    ]
    
    @classmethod
    def get_or_create_default_roles(cls):
        """Create default roles if they don't exist."""
        created_roles = []
        for code, name in cls.ROLE_CHOICES:
            role, created = cls.objects.get_or_create(name=code)
            if created:
                created_roles.append(role)
        return created_roles
