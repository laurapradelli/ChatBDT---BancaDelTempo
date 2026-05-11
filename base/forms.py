from django import forms
from django.forms import ModelForm, DateInput, SelectMultiple
from .models import User, Scambio, Evento, Area, Categoria, BDT


class DateInput(forms.DateInput):
    input_type = 'date'

class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'

class FiltroDate(forms.Form):
    data_inizio = forms.DateField(widget=DateInput())
    data_fine = forms.DateField(widget=DateInput())


class UserForm(ModelForm):
    quota = forms.BooleanField(required=False, label='quota')
    class Meta:
        model = User
        fields = ['nome', 'cognome', 'nascita', 'residenza', 'cf', 'telefono', 'email']
        widgets = {
            'nascita': DateInput()
        }

class TesUserForm(ModelForm):
    class Meta:
        model = User
        fields = ['nome', 'cognome', 'nascita', 'residenza', 'cf', 'telefono', 'email', 'quota', 'ore_iniz']
        widgets = {
            'nascita': DateInput(),
            'quota': forms.CheckboxInput()
        }


class CreateUserForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        self.fields['nome'].required = True
        self.fields['cognome'].required = True
        self.fields['cf'].required = True
        self.fields['email'].required = True
        self.fields['nascita'].required = False
        self.fields['residenza'].required = False
        self.fields['telefono'].required = False
        self.fields['ore_iniz'].required = False

    class Meta:
        model = User
        fields = ['nome', 'cognome', 'nascita', 'residenza', 'cf', 'telefono', 'email', 'quota', 'ore_iniz']
        widgets = {
            'nascita': DateInput(),
            'quota': forms.CheckboxInput()
        }



class CreateScambioForm(ModelForm):
    def __init__(self, *args, **kwargs):
        tesorieri = kwargs.pop('tesorieri', [])
        super(CreateScambioForm, self).__init__(*args, **kwargs)
        self.fields['area'].required = False
        self.fields['note'].required = False

        # Filtra gli utenti per il campo 'bdt' specificato, che viene passato da views.py
        bdt_value = kwargs.get('initial', {}).get('bdt', None)
        if bdt_value:
            self.fields['donatori'].queryset = User.objects.filter(bdt=bdt_value).exclude(id__in=tesorieri)
            self.fields['riceventi'].queryset = User.objects.filter(bdt=bdt_value).exclude(id__in=tesorieri)
            self.fields['area'].queryset = Area.objects.filter(bdt=bdt_value)

        self.fields['donatori'].widget.attrs.update({'class': 'custom-select-multiple'})
        self.fields['riceventi'].widget.attrs.update({'class': 'custom-select-multiple'})
    
    class Meta:
        model = Scambio
        fields = ['donatori', 'riceventi', 'durata', 'data', 'area', 'note']
        widgets = {
            'data': DateInput(),
            'donatori': SelectMultiple(),
            'riceventi': SelectMultiple(),
        }


class CreateEventoForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(CreateEventoForm, self).__init__(*args, **kwargs)
        self.fields['foto'].required = False
        self.fields['descrizione'].widget.attrs.update({'class': 'descrizione-evento'})


    class Meta:
        model = Evento
        fields = ['foto', 'titolo', 'descrizione', 'data_ora']
        widgets = {
            'data_ora': DateTimeInput()
        }


class CreateAreaForm(ModelForm):
    class Meta:
        model = Area
        fields = ['nome']

class CreateCategoriaForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(CreateCategoriaForm, self).__init__(*args, **kwargs)
        bdt_value = kwargs.get('initial', {}).get('bdt', None)
        if bdt_value:
            self.fields['area'].queryset = Area.objects.filter(bdt=bdt_value)

    class Meta:
        model = Categoria
        fields = ['nome', 'area']

    


class CreateBDTForm(ModelForm):
    class Meta:
        model = BDT
        fields = ['nome_bdt', 'logo_bdt']


class CreateTesoriereForm(ModelForm):
    class Meta:
        model = User
        fields = ['nome', 'cognome', 'email']


class FiltraScambi(ModelForm):
    def __init__(self, *args, **kwargs):
        super(FiltraScambi, self).__init__(*args, **kwargs)
        bdt_value = kwargs.get('initial', {}).get('bdt', None)
        if bdt_value:
            self.fields['area'].queryset = Area.objects.filter(bdt=bdt_value)

    class Meta:
        model = Scambio
        fields = ['area']
        
    REQUIRED_FIELDS = []
