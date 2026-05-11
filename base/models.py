from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext as _
from django.utils import timezone


class BDT(models.Model):
    nome_bdt = models.CharField(max_length=100, null=True)
    logo_bdt = models.ImageField(null=True, default="no-image.png")

    def __str__(self):
        return self.nome_bdt
    

class Area(models.Model):
    nome = models.CharField(max_length=200)
    bdt = models.ForeignKey(BDT, on_delete=models.SET_NULL, null=True)
    
    class Meta:
            ordering = ['nome']

    def __str__(self):
        return self.nome
    
class Categoria(models.Model):
    nome = models.CharField(max_length=300)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True)
    bdt = models.ForeignKey(BDT, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome
    
    

class User(AbstractUser):
    nome = models.CharField(max_length=50, null=True)
    cognome = models.CharField(max_length=50, null=True)
    nascita = models.DateField(null=True)
    cf = models.CharField(max_length=16, null=True)
    residenza = models.CharField(max_length=100, null=True)
    telefono = models.CharField(max_length=10, null=True)
    email = models.EmailField(max_length=50, null=True, unique=True)
    bdt = models.ForeignKey(BDT, on_delete=models.SET_NULL, null=True)
    quota = models.BooleanField(null=True, default=False)
    tesoriere = models.BooleanField(default=False, null=True)
    propensione = models.ManyToManyField(Area, related_name="propensione")
    saldo = models.IntegerField(null=True, default=0)
    ore_iniz = models.IntegerField(null=True, default=0)
    anni_pag = models.TextField(null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        if self.tesoriere:
            return "Sig. Banca del Tempo"
        else:
            if self.cognome and self.nome:
                nome_cognome = str(self.cognome+ " "+self.nome)
            else:
                nome_cognome = "ciao"
            return nome_cognome
    
    class Meta:
        ordering = ['cognome']

    

class Evento(models.Model):
    foto = models.ImageField(null=True, default="no-image.png")
    titolo = models.CharField(max_length=50)
    descrizione = models.TextField()
    data_ora = models.DateTimeField()
    bdt = models.ForeignKey(BDT, on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.titolo
    
    class Meta:
        ordering = ['-created']
    


class Scambio(models.Model):
    donatori = models.ManyToManyField(User, related_name="donatori")
    riceventi = models.ManyToManyField(User, related_name="riceventi")
    data = models.DateField()
    durata = models.IntegerField()
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)
    note = models.TextField()
    bdt = models.ForeignKey(BDT, on_delete=models.SET_NULL, null=True)
    nomi_donatori = models.CharField(max_length=500, null=True)
    nomi_riceventi = models.CharField(max_length=500, null=True)
    
    REQUIRED_FIELDS = ['donatori', 'riceventi', 'data', 'durata']
