from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime, timedelta, date
from .models import User, Evento, Scambio, Categoria, Area, BDT
from .forms import UserForm, CreateUserForm, CreateScambioForm, TesUserForm, CreateEventoForm, CreateAreaForm, CreateCategoriaForm, FiltraScambi, FiltroDate
from .forms import CreateTesoriereForm, CreateBDTForm
from email.message import EmailMessage
import smtplib
import random
import json
import openpyxl
import os
from io import BytesIO

# Create your views here.

def filtraScambi(request):
    if request.method == "POST":
        filtrati = Scambio.objects.filter(bdt=request.user.bdt)

        if request.POST.get('area'):
            filtrati = filtrati.filter(
                Q(area=request.POST.get('area'))
            )
        
        if request.POST.get('data_inizio') and request.POST.get('data_fine'):
            request.session['data_inizio'] = request.POST.get('data_inizio')
            request.session['data_fine'] = request.POST.get('data_fine')
            filtrati = filtrati.filter(
                Q(data__gte=request.POST.get('data_inizio')) &
                Q(data__lte=request.POST.get('data_fine'))
            ).order_by('-data')

    return render(request, 'base/tabellaScambi.html', {'scambi': filtrati})


def search_view(request):
    query = request.GET.get('query', '')
    results = User.objects.filter(nome__icontains=query)[:10]
    # Restituisci i risultati come JSON
    data = [{'id': obj.id, 'nome': obj.nome} for obj in results]
    return JsonResponse(data, safe=False)



def search_users(request):
    searchText = request.GET.get('search_text')
    users = User.objects.filter(bdt=request.user.bdt, nome__icontains=searchText).values_list('nome', 'cognome', 'id')
    dict_users = {}
    for user in users:
        dict_users[user[0]+" "+user[1]] = user[2]
    return JsonResponse({'users': dict_users})


def get_categories(request):
    area_id = request.GET.get('area_id')
    categories = Categoria.objects.filter(area_id=area_id).values_list('id', 'nome')
    return JsonResponse({'categories': dict(categories)})


def saldo(user, scambi):
    #scambi = Scambio.objects.filter(bdt=user.bdt)
    dati = {'ore_date':0, 'ore_ricevute':0, 'saldo':0, 'tesoretto':0}
    dati['saldo'] += user.ore_iniz
    for scambio in scambi:
        no = 0
        donatori = scambio.donatori.all()
        for donatore in donatori:
            if user == donatore:
                dati["saldo"] += scambio.durata
                dati["ore_date"] += scambio.durata
            if donatore.tesoriere:
                no += 1
                
        riceventi = scambio.riceventi.all()
        
        for ricevente in riceventi:
            if user == ricevente:
                dati["saldo"] -= scambio.durata
                dati["ore_ricevute"] -= scambio.durata
            if ricevente.tesoriere:
                no += 1

        if user.tesoriere:
            ore_date = 0
            ore_ric = 0
            for scambio_2 in scambi:
                for donatore in scambio_2.donatori.all():
                    if donatore.tesoriere:
                        ore_date += scambio_2.durata
                for ricevente in scambio_2.riceventi.all():
                    if ricevente.tesoriere:
                        ore_ric += scambio_2.durata
            dati["ore_date"] = ore_date
            dati["ore_ric"] = ore_ric

            if len(scambio.donatori.all())<len(scambio.riceventi.all()) and no == 0:
                dati["tesoretto"] += (scambio.durata*len(donatori)*(len(riceventi)-1))

    return dati


def loginPage(request):
    mess = 0
    if request.method=="POST":
        email=request.POST.get('email').lower()
        password=request.POST.get('password')

        try:
            user = User.objects.get(username=email)
        except:
            mess += 1
            messages.warning(request, "Non abbiamo trovato questa mail nei nostri sistemi :(")

        user = authenticate(request, username=email, password=password)  

        if user is not None:
            login(request, user)
            return redirect('profilo', pk=user.id)
        else:
            mess+=1
            messages.warning(request, "Password errata, riprova!")

    return render(request, 'base/login.html', {'mess':mess})


def recuperaPassword(request):
    mess = 0
    if request.method=="POST":
        email = request.POST.get('email')
        esiste = False
        try:
            user = User.objects.get(email=email)
            nome_senzaspazi = user.nome.replace(" ", "")
            cognome_senzaspazi = user.cognome.replace(" ", "")
            num = random.randint(1, 1000)
            password = nome_senzaspazi + cognome_senzaspazi + str(num)
            password = password.lower()
            psw_hashed = make_password(password)
            user.password = psw_hashed
            user.save()
            esiste = True
        except ObjectDoesNotExist:
            mess += 1
            messages.warning(request, "La mail inserita non è nei nostri sistemi :(")

        if esiste:
            smtp_server = 'smtp.gmail.com'
            smtp_port = 587
            smtp_username = "ChatBDT"
            smtp_password = os.environ.get('EMAIL_HOST_PASSWORD')
            sender = os.environ.get('EMAIL_HOST_USER')
            subject = "Recupero password - ChatBDT"
            message = "Ciao,\nabbiamo ricevuto una richiesta per il ripristino della password.\nEcco a te la nuova password che puoi usare per entrare su ChatBDT: "+password+"\nTi consigliamo di cambiare subito questa password, non è sicura!\nIl team di ChatBDT"
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = email
            msg.set_content(message)
            try:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()  # Avvia una connessione sicura
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
                server.quit()
                return redirect("mail_inviata")
            except Exception as e:
                print("Si è verificato un errore durante l'invio dell'email:", str(e))

    return render(request, "base/recuperoPassword.html", {'mess':mess})
    
def mailInviata(request):
    return render(request, "base/mailInviata.html")

def userInesistente(request):
    return render(request, "base/userInesistente.html")

def changePassword(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    mess=0
    if request.method=="POST":
        nuova = request.POST.get("nuova")
        ripeti = request.POST.get("ripeti")

        if nuova == ripeti:
            user = User.objects.get(id=request.user.id)
            user.password = make_password(nuova)
            user.save()
        else:
            mess+=1
            messages.warning(request, 'Cambio password effettuato con successo!')
    context = {'bdt':bdt, 'mess':mess}
    return render(request, 'base/change_password.html', context)


@login_required(login_url='/login')
def logoutPage(request):
    logout(request)
    return redirect('home')


def home(request):
    eventi = Evento.objects.all().order_by('-data_ora')
    eventi_ok = []
    data_vecchia = (timezone.now()-timedelta(days=90))
    somma_3mesi = data_vecchia.month + data_vecchia.year
    for evento in eventi:
        somma_evento = evento.data_ora.month + evento.data_ora.year
        if somma_evento > somma_3mesi:
            eventi_ok.append(evento)
    context = {"eventi":eventi_ok}
    return render(request, 'base/home.html', context)



######################   CRUD SOCI   ######################
@login_required(login_url='/login')
def createSocio1(request):
    user = request.user
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    form = CreateUserForm()
    mess = 0
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.username = new_user.email
            nome_senzaspazi = new_user.nome.replace(" ", "")
            cognome_senzaspazi = new_user.cognome.replace(" ", "")
            password = nome_senzaspazi + cognome_senzaspazi
            password = password.lower()
            psw_hashed = make_password(password)
            new_user.password = psw_hashed
            new_user.bdt = user.bdt
            quota = form.cleaned_data['quota']
            new_user.anni_pag = ''
            if quota:
                new_user.quota=True
                new_user.anni_pag += str(timezone.now().year)
            else:
                new_user.quota=False
                new_user.anni_pag = ""
            new_user.save()
            return redirect('create_socio_categorie', pk=new_user.id)
        else:
            mess+=1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'user':user, 'form':form, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/createSocio.html', context)

@login_required(login_url='/login')
def createSocio2(request, pk):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    new_user = User.objects.get(id=pk)
    aree = Area.objects.filter(bdt=request.user.bdt)
    if request.method=="POST":
        selezionate = request.POST.getlist('area_selezionata')
        new_user.propensione.set(selezionate)
        new_user.save()
        return redirect('tes_profilo_socio', pk=new_user.id)
    context = {'bdt':bdt, 'aree':aree, 'new_user':new_user}
    return render(request, 'base/createSocio2.html', context)

@login_required(login_url='/login')
def updateSocio(request, pk):
    mess = 0
    user = User.objects.get(id=pk)
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    user2 = user
    user2.nascita = user.nascita.strftime('%Y-%m-%d')
    quota_old = user.quota
    if request.user.tesoriere:
        form = TesUserForm(instance=user2)
    else:
        form = UserForm(instance=user2)
    if request.method == 'POST':
        if request.user.tesoriere:
            form = TesUserForm(request.POST, request.FILES, instance=user)
        else:
            form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            quota_agg = form.cleaned_data['quota']
            user.anni_pag = ''
            if quota_agg:
                user.anni_pag += str(timezone.now().year) 
            elif not quota_agg and quota_agg != quota_old:      #se viene modificata e passa da true a false
                user.anni_pag = user.anni_pag[:-4]
            print(user.anni_pag)
            user.save()
            if request.user.tesoriere:
                return redirect('tes_profilo_socio', pk=user2.id)
            else:
                return redirect('profilo', pk=user2.id)
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'form':form, 'user':user, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/updateUser.html', context)


@login_required(login_url='/login')
def deleteSocio(request, pk):
    socio = User.objects.get(id=pk)
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    if request.method=="POST":
        socio.delete()
        return redirect('profilo', pk=request.user.id)
    context = {'obj':socio, 'bdt':bdt}
    return render(request, 'base/delete.html', context)


@login_required(login_url='/login')
def showSoci(request):
    soci = User.objects.filter(bdt=request.user.bdt)    
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    if " " in q:
        nome = q.split(" ")[0]

        try:
            cognome = q.split(" ")[1]+q.split(" ")[2]
        except:
            cognome = q.split(" ")[1]
        
        soci = soci.filter(
            Q(nome__icontains=nome) |
            Q(cognome__icontains=cognome)
        )
    else:
        soci = soci.filter(
            Q(nome__icontains=q) |
            Q(cognome__icontains=q)
        )
    tutti = len(soci)
    meta = len(soci)/2
    prima_meta = []
    sec_meta = []
    for i in range(0, int(meta)):
        prima_meta.append(soci[i])
    for i in range(int(meta), int(tutti)):
        sec_meta.append(soci[i])
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    context = {'soci':soci, 'bdt':bdt, 'prima_meta':prima_meta, 'sec_meta':sec_meta}
    return render(request, 'base/showSoci.html', context)


def infoSoci(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    users = User.objects.filter(bdt=request.user.bdt).order_by('cognome')
    context = {'bdt':bdt, 'users':users}
    return render(request, 'base/infoSoci.html', context)

######################   FINE CRUD SOCIO   ######################


######################   CRUD SCAMBIO   ######################
@login_required(login_url='/login')
def createScambio(request):
    user = request.user
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    users = User.objects.filter(bdt=bdt)
    mess = 0
    tesorieri = []
    for user in users:
        if user.tesoriere and user!=request.user:
            tesorieri.append(user.id)
    categorie = Categoria.objects.filter(bdt=request.user.bdt)
    aree = Area.objects.filter(bdt=request.user.bdt)
    
    if request.method == 'POST':
        form = CreateScambioForm(request.POST, initial={'bdt': bdt}, tesorieri=tesorieri)
        nome_categoria = request.POST.get('categoria')
        conivolti_diversi=True
        for donatore in request.POST.getlist('donatori'):
            for ricevente in request.POST.getlist('riceventi'):
                if donatore == ricevente:
                    conivolti_diversi=False


        if form.is_valid() and conivolti_diversi:
            scambio = form.save(commit=False)
            scambio.bdt = user.bdt
            if nome_categoria != "":
                try:
                    categoria = Categoria.objects.get(nome=nome_categoria)
                except:
                    Categoria.objects.create(
                        nome=nome_categoria,
                        area=scambio.area,
                        bdt=request.user.bdt
                    )
                    categoria = Categoria.objects.get(nome=nome_categoria)
                scambio.categoria = categoria
            ids_donatori = request.POST.getlist('donatori')
            ids_riceventi = request.POST.getlist('riceventi')
            don = ''
            ric = ''
            for id in ids_donatori:
                don += (User.objects.get(id=id).nome+User.objects.get(id=id).cognome)
            for id in ids_riceventi:
                ric += (User.objects.get(id=id).nome+User.objects.get(id=id).cognome)
            don = don.replace(" ", "")
            ric = ric.replace(" ", "")
            scambio.nomi_donatori = don
            scambio.nomi_riceventi = ric
            scambio.save()
            scambio.donatori.add(*ids_donatori)
            scambio.riceventi.add(*ids_riceventi) 
            
            return redirect('show_scambi')
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    else:
        bdt_value = user.bdt
        form = CreateScambioForm(initial={'bdt': bdt_value}, tesorieri=tesorieri)
    context = {'user':user, 'form':form, 'bdt':bdt, 'categorie':categorie}
    return render(request, 'base/createScambio.html', context)


@login_required(login_url='/login')
def updateScambio(request, pk):
    mess = 0
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    scambio = Scambio.objects.get(id=pk)
    scambio2 = scambio
    scambio2.data = scambio.data.strftime('%Y-%m-%d')
    tesorieri = []
    form = CreateScambioForm(instance=scambio2, tesorieri=tesorieri)
    users = User.objects.filter(bdt=bdt)
    
    for user in users:
        if user.tesoriere and user!=request.user:
            tesorieri.append(user.id)
    if request.method=="POST":
        form = CreateScambioForm(request.POST, request.FILES, instance=scambio2, tesorieri=tesorieri)
        if form.is_valid():
            form.save()
            ids_donatori = request.POST.getlist('donatori')
            scambio.donatori.add(*ids_donatori)
            ids_riceventi = request.POST.getlist('riceventi')
            scambio.riceventi.add(*ids_riceventi)             
            scambio.save()
            return redirect('show_scambi')  
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    else:
        bdt_value = request.user.bdt
        form = CreateScambioForm(initial={'bdt': bdt_value}, instance=scambio2, tesorieri=tesorieri)

    context = {'form':form, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/updateScambio.html', context)


@login_required(login_url='/login')
def deleteScambio(request, pk):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    scambio = Scambio.objects.get(id=pk)
    if request.method=="POST":
        scambio.delete()
        return redirect('show_scambi')
    donatori = ""
    riceventi = ""

    for don in scambio.donatori.all():
        if don.tesoriere:
            donatori += "Sig. Banca del Tempo"
        else:
            donatori += don.nome+" "+don.cognome+" "
    if donatori == "":
        donatori = "Socio eliminato"

    for ric in scambio.riceventi.all():
        if ric.tesoriere:
            riceventi += "Sig. Banca del Tempo"
        else:
            riceventi += ric.nome+" "+ric.cognome+" "
    if riceventi == "":
        riceventi = "Socio eliminato"


    dati_scambio = str(donatori) + " - " + str(riceventi) + ", " + str(scambio.area)
    context = {'obj':dati_scambio, 'bdt':bdt}
    return render(request, 'base/delete.html', context)


@login_required(login_url='/login')
def showScambi(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    scambi_v = Scambio.objects.filter(bdt=request.user.bdt).order_by('-data')
    form = FiltraScambi(initial={'bdt': bdt})
    formDate = FiltroDate()
    context = {'scambi':scambi_v, 'bdt':bdt, 'form':form, 'form_date':formDate}
    return render(request, 'base/showScambi.html', context)

######################   FINE CRUD SCAMBIO   ######################


######################   CRUD EVENTO   ######################
@login_required(login_url='/login')
def createEvento(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    form = CreateEventoForm()
    mess = 0
    if request.method == 'POST':
        form = CreateEventoForm(request.POST, request.FILES)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.bdt = request.user.bdt
            evento.save()
            return redirect('show_eventi')
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'form':form, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/createEvento.html', context)


@login_required(login_url='/login')
def updateEvento(request, pk):
    mess = 0
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    evento = Evento.objects.get(id=pk)
    evento2 = evento
    evento2.data_ora = evento.data_ora.strftime('%Y-%m-%d %H:%m')
    form = CreateEventoForm(instance=evento2)
    if request.method=="POST":
        form = CreateEventoForm(request.POST, instance=evento2)
        if form.is_valid():
            form.save()
            return redirect('show_eventi')
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'form':form, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/updateEvento.html', context)


@login_required(login_url='/login')
def deleteEvento(request, pk):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    evento = Evento.objects.get(id=pk)
    if request.method=="POST":
        evento.delete()
        return redirect('show_eventi')
    context = {'obj':evento, 'bdt':bdt}
    return render(request, 'base/delete.html', context)


@login_required(login_url='/login')
def showEventi(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    eventi = Evento.objects.filter(bdt=bdt).order_by('-data_ora')
    context = {'eventi':eventi, 'bdt':bdt}
    return render(request, 'base/showEventi.html', context)

######################   FINE CRUD EVENTO   ######################

######################  CRUD AREE - CATEGORIE  ######################
@login_required(login_url='/login')
def createArea(request):
    form = CreateAreaForm()
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    mess = 0
    if request.method=="POST":
        form = CreateAreaForm(request.POST)
        if form.is_valid():
            area = form.save(commit=False)
            area.bdt = request.user.bdt
            area.save()
            return redirect('show_aree_categorie')
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'form':form, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/createArea.html', context)


@login_required(login_url='/login')
def updateArea(request, pk):
    mess = 0
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    area = Area.objects.get(id=pk)
    form = CreateAreaForm(instance=area)
    if request.method=="POST":
        form = CreateAreaForm(request.POST, instance=area)
        if form.is_valid():
            up_area = form.save(commit=False)
            up_area.bdt=request.user.bdt
            up_area.save()
            return redirect('show_aree_categorie')
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'form':form, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/updateArea.html', context)



@login_required(login_url='/login')
def deleteArea(request, pk):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    area = Area.objects.get(id=pk)
    if request.method=="POST":
        area.delete()
        return redirect('show_aree_categorie')
    context = {'obj':area, 'bdt':bdt}
    return render(request, 'base/delete.html', context)


@login_required(login_url='/login')
def createCategoria(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    form = CreateCategoriaForm(initial={'bdt': bdt})
    mess = 0
    if request.method=="POST":
        form = CreateCategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.bdt = request.user.bdt
            categoria.save()
            return redirect('show_aree_categorie')
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'form':form, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/createCategoria.html', context)


@login_required(login_url='/login')
def updateCategoria(request, pk):
    mess = 0
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    categoria = Categoria.objects.get(id=pk)
    form = CreateCategoriaForm(instance=categoria)
    if request.method=="POST":
        form = CreateCategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            up_categoria = form.save(commit=False)
            up_categoria.bdt=request.user.bdt
            up_categoria.save()
            return redirect('show_aree_categorie')
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'form':form, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/updateCategoria.html', context)


@login_required(login_url='/login')
def deleteCategoria(request, pk):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    categoria = Categoria.objects.get(id=pk)
    if request.method=="POST":
        categoria.delete()
        return redirect('show_aree_categorie')
    context = {'obj':categoria, 'bdt':bdt}
    return render(request, 'base/delete.html', context)


@login_required(login_url='/login')
def showAreeCategorie(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    aree = Area.objects.filter(bdt=request.user.bdt)
    categorie = Categoria.objects.filter(bdt=request.user.bdt)
    context = {'aree':aree, 'categorie':categorie, 'bdt':bdt}
    return render(request, 'base/showAreeCategorie.html', context)

######################  FINE CRUD AREE - CATEGORIE  ######################

######################  CRUD BDT  ######################
@login_required(login_url='/login')
def createBDT(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    form_bdt = CreateBDTForm()
    form_tes = CreateTesoriereForm()
    mess = 0
    if request.method=="POST":
        form_bdt = CreateBDTForm(request.POST, request.FILES)
        form_tes = CreateTesoriereForm(request.POST, request.FILES)
        if form_bdt.is_valid() and form_tes.is_valid():
            new_bdt = form_bdt.save(commit=False)
            new_bdt.save()
            tesoriere = form_tes.save(commit=False)
            tesoriere.bdt = new_bdt
            tesoriere.username = tesoriere.email
            nome_senzaspazi = tesoriere.nome.replace(" ", "")
            cognome_senzaspazi = tesoriere.cognome.replace(" ", "")
            password = nome_senzaspazi + cognome_senzaspazi
            password = password.lower()
            psw_hashed = make_password(password)
            tesoriere.password = psw_hashed
            tesoriere.tesoriere = True
            tesoriere.save()
            return redirect('profilo', pk=request.user.id)
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'bdt':bdt, 'form_bdt':form_bdt, 'form_tes':form_tes, 'mess':mess}
    return render(request, 'base/createBDT.html', context)

@login_required(login_url='/login')
def updateBDT(request):
    mess = 0
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    form = CreateBDTForm(instance=bdt)
    if request.method=="POST":
        form = CreateBDTForm(request.POST, request.FILES, instance=bdt)
        if form.is_valid():
            form.save()
            return redirect('profilo', pk=request.user.id)
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'bdt':bdt, 'form':form, 'mess':mess}
    return render(request, 'base/updateBDT.html', context)

@login_required(login_url='/login')
def deleteBDT(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    if request.method=="POST":
        users = User.objects.filter(bdt=bdt)
        for user in users:
            user.delete()
        scambi = Scambio.objects.filter(bdt=bdt)
        for scambio in scambi:
            scambio.delete()
        eventi = Evento.objects.filter(bdt=bdt)
        for evento in eventi:
            evento.delete()
        aree = Area.objects.filter(bdt=bdt)
        for area in aree:
            area.delete()
        categorie = Categoria.objects.filter(bdt=bdt)
        for categoria in categorie:
            categoria.delete()
        bdt.delete()
        return redirect('home')
    context = {'obj':bdt, 'bdt':bdt}
    return render(request, 'base/delete.html', context)




###################### FINE  CRUD BDT  ######################

###################### CRUD TESORIERI #######################

@login_required(login_url='/login')
def createTesoriere(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    form = CreateTesoriereForm()
    mess = 0
    if request.method == "POST":
        form = CreateTesoriereForm(request.POST)
        if form.is_valid():
            tesoriere = form.save(commit=False)
            tesoriere.bdt = bdt
            tesoriere.username = tesoriere.email
            nome_senzaspazi = tesoriere.nome.replace(" ", "")
            cognome_senzaspazi = tesoriere.cognome.replace(" ", "")
            password = nome_senzaspazi + cognome_senzaspazi
            password = password.lower()
            psw_hashed = make_password(password)
            tesoriere.password = psw_hashed
            tesoriere.tesoriere = True
            tesoriere.save()
            return redirect('show_tesorieri')
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'form':form, 'bdt':bdt, 'mess':mess}
    return render(request, 'base/createTesoriere.html', context)


@login_required(login_url='/login')
def updateTesoriere(request, pk):
    mess = 0
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    tes = User.objects.get(id=pk)
    form = CreateTesoriereForm(instance=tes)
    if request.method == "POST":
        form = CreateTesoriereForm(request.POST, instance=tes)
        if form.is_valid():
            form.save()
            return redirect('show_tesorieri')
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    context = {'bdt':bdt, 'form':form, 'mess':mess}
    return render(request, 'base/updateTesoriere.html', context)


@login_required(login_url='/login')
def deleteTesoriere(request, pk):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    tes = User.objects.get(id=pk)
    tes_nome = "Tesoriere " + User.objects.get(id=pk).nome + " " + User.objects.get(id=pk).cognome
    if request.method == "POST":
        tes.delete()
        return redirect('show_tesorieri')
    context = {'obj':tes_nome, 'bdt':bdt}
    return render(request, 'base/delete.html', context)


@login_required(login_url='/login')
def showTesorieri(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    tesorieri = User.objects.filter(tesoriere=True, bdt=bdt)
    context = {'bdt':bdt, 'tesorieri':tesorieri}
    return render(request, 'base/showTesorieri.html', context)


###################### FINE CRUD TESORIERI ##################



@login_required(login_url='/login')
def tes_profiloSocio(request, pk):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    user = User.objects.get(id=pk)
    scambi_d = Scambio.objects.filter(donatori=pk).order_by('data')
    scambi_r = Scambio.objects.filter(riceventi=pk).order_by('data')
    scambi = Scambio.objects.filter(bdt=user.bdt).order_by('data')
    scambi_tes = []
    scambi_sig = []
    scambi_sig_dor = {}
    no = 0

    for scambio in scambi:
        for donatore in scambio.donatori.all():
            if donatore.tesoriere:
                scambi_sig.append(scambio)
                scambi_sig_dor[0] = scambio     #se la chiave è 0, il sig banca del tempo è donatore (ore +)
        for ricevente in scambio.riceventi.all():
            if ricevente.tesoriere:
                scambi_sig.append(scambio)
                scambi_sig_dor[1] = scambio     #se la chiave è 1, il sig banca del tempo è ricevente (ore -)


    for scambio in scambi:
        no = 0
        if len(scambio.donatori.all()) < len(scambio.riceventi.all()):
            for donatore in scambio.donatori.all():
                if donatore.tesoriere:
                    no += 1
            for ricevente in scambio.donatori.all():
                if ricevente.tesoriere:
                    no += 1
            if no == 0:
                scambi_tes.append(scambio)

    ultimo_d = date(2000, 1, 1)
    ultimo_r = date(2000, 1, 1)

    for scambio in scambi_d:
        ultimo_d = scambio.data
        
    for scambio in scambi_r:
        ultimo_r = scambio.data

    if ultimo_d > ultimo_r:
        ultimo = ultimo_d
    else:
        ultimo = ultimo_r

    if ultimo > timezone.now().date()-timedelta(days=365):
        attivo = True
    else:
        attivo = False

    if ultimo == date(2000, 1, 1):
        ultimo = "Mai"

    dati_utente = saldo(user, scambi)
    saldo_utente = 0
    if user.tesoriere:
        for tipo, scambio in scambi_sig_dor.items():
            if tipo == 0:
                saldo_utente = saldo_utente + scambio.durata
            elif tipo == 1:
                saldo_utente = saldo_utente - scambio.durata
    else:
        saldo_utente = dati_utente["saldo"]

    if user.tesoriere:
        tesoretto = dati_utente["tesoretto"]
    else:
        tesoretto = 0

    if user.anni_pag:
        ultimo_pag = user.anni_pag[-4:]
    else:
        ultimo_pag = ""

    if ultimo_pag != str(timezone.now().year):          #se non è ancora stato fatto il pagamento per l'anno corrente
        user.quota = False
        user.save()

    context = {'user':user, 'bdt':bdt, 'saldo':saldo_utente, 'scambi_sig':scambi_sig, 'scambi_d':scambi_d, 'scambi_r':scambi_r, 'scambi_tes':scambi_tes, 'tesoretto':tesoretto, 'attivo':attivo, 'ultimo':ultimo}
    return render(request, 'base/tes_profiloSocio.html', context)



@login_required(login_url='/login')
def dettaglioQuota(request, pk):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    user = User.objects.get(id=pk)
    if user.anni_pag:
        lista_anni_pag = [user.anni_pag[i:i+4] for i in range(0, len(user.anni_pag), 4)]
        lista_anni = {}
        for anno in range(user.date_joined.year, timezone.now().year+1):
            if str(anno) in lista_anni_pag:
                lista_anni[anno] = "Pagata"
            else:
                lista_anni[anno] = "Non Pagata"
    else:
        lista_anni = {}
        
    context = {'bdt':bdt, 'lista_anni':lista_anni, 'user':user}
    return render(request, 'base/dettaglioQuote.html', context)
    



@login_required(login_url='/login')
def oreSoci(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    mess = 0
    form = FiltroDate()
    data_fine = timezone.now()
    data_inizio = datetime(2000, 1, 1)
    users = User.objects.filter(bdt=bdt)
    id_tes = []
    for user in users:
        if user.tesoriere and user!=request.user:
            id_tes.append(user.id)
    scambi = Scambio.objects.filter(bdt=request.user.bdt)
    scambi = scambi.exclude(id__in=id_tes)
    saldi = {}
    tot_date = 0
    tot_ric = 0
    for user in users:
        dati = saldo(user, scambi)
        if user!=request.user:
            tot_date += dati["ore_date"]
            tot_ric += dati["ore_ricevute"]*(-1)
        dati.pop("tesoretto")
        saldi[user] = dati


    if request.method == "POST":
        form = FiltroDate(request.POST)
        if form.is_valid():
            tot_date = 0
            tot_ric = 0
            data_inizio = form.cleaned_data['data_inizio']
            data_fine = form.cleaned_data['data_fine']
            scambi = Scambio.objects.filter(bdt=bdt, data__range=[data_inizio, data_fine])
            for user in users:
                dati = saldo(user, scambi)
                tot_date += dati["ore_date"]
                tot_ric += dati["ore_ricevute"]*(-1)
                dati.pop("tesoretto")
                saldi[user] = dati 
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')   
    periodo = str(data_inizio.strftime("%d/%m/%Y")) + " - " + str(data_fine.strftime("%d/%m/%Y"))
    context = {'saldi':saldi, 'bdt':bdt, 'form':form, 'periodo':periodo, 'tot_date':tot_date, 'tot_ric':tot_ric, 'mess':mess}
    return render(request, 'base/oreSoci.html', context)


@login_required(login_url='/login')
def profiloSocio(request, pk):
    user = User.objects.get(id=pk)
    try:
        bdt = BDT.objects.get(nome_bdt=user.bdt)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("La tua bdt è stata eliminata.")
    scambi = Scambio.objects.filter(bdt=user.bdt).order_by('-data')
    scambi_in = []
    for scambio in scambi:
        donatori = scambio.donatori.all()
        riceventi = scambio.riceventi.all()
        if user in donatori or user in riceventi:
            scambi_in.append(scambio)
    users = User.objects.filter(bdt=user.bdt).order_by('cognome')
    saldi = {}
    saldi_users = []
    for user in users:
        dati = saldo(user, scambi)
        saldi[user] = dati["saldo"]
        saldi_users.append(dati["saldo"])
    context = {'user':user, 'bdt':bdt, 'users':users, 'scambi':scambi_in, 'saldi':saldi, 'saldi_users':saldi_users}
    return render(request, 'base/homeSocio.html', context)


def get_nscambi(request, data_inizio, data_fine):
    scambi = Scambio.objects.filter(bdt=request.user.bdt, data__gte=data_inizio, data__lte=data_fine)
    dati = {}
    for scambio in scambi:
        data = scambio.data.strftime("%d/%m/%Y")
        data_datetime = datetime.strptime(data, "%d/%m/%Y").date()
        if data_datetime in dati:
            dati[data_datetime] += 1
        else:
            dati[data_datetime] = 1
    ordinati = dict(sorted(dati.items()))
    scambi_periodo = {}
    for data, numero in ordinati.items():
        scambi_periodo[data.strftime("%d/%m/%Y")]=numero
    return json.dumps(scambi_periodo)

def get_scambiPersona(request, data_inizio, data_fine):
    scambi = Scambio.objects.filter(data__lte=data_fine, data__gte=data_inizio)
    personeScambi = {}
    users = User.objects.filter(bdt=request.user.bdt)
    for user in users:
        personeScambi[user] = 0
    for scambio in scambi:
        for donatore in scambio.donatori.all():
                personeScambi[donatore] += 1
        for ricevente in scambio.riceventi.all():
                personeScambi[ricevente] += 1
    personeScambi_ord = dict(sorted(personeScambi.items(), key=lambda item: item[1], reverse=True))
    personeScambi_dieci = dict(list(personeScambi_ord.items())[:10])
    return personeScambi_dieci


def get_scambiCat(request, data_inizio, data_fine):
    scambi = Scambio.objects.filter(data__lte=data_fine, data__gte=data_inizio)
    catScambi = {}
    cats = Area.objects.filter(bdt=request.user.bdt)
    for cat in cats:
        catScambi[cat] = 0
    for scambio in scambi:
        catScambi[scambio.area] += 1

    catOrd = dict(sorted(catScambi.items(), key=lambda item:item[1], reverse=True))
    catOrd_dieci = dict(list(catOrd.items())[:10])
    return catOrd_dieci


@login_required(login_url='/login')
def statistiche(request):
    mess = 0
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    form = FiltroDate()
    data_fine = timezone.now()
    data_inizio = timezone.now()-timedelta(30)
    periodo = f'{data_inizio.strftime("%d/%m/%Y")} - {data_fine.strftime("%d/%m/%Y")}'
    scambi_periodo = get_nscambi(request, data_inizio, data_fine)
    if request.method=="POST":
        form = FiltroDate(request.POST)
        if form.is_valid():
            data_inizio = form.cleaned_data['data_inizio']
            data_fine = form.cleaned_data['data_fine']
            scambi_periodo = get_nscambi(request, data_inizio, data_fine)
            periodo = f'{data_inizio.strftime("%d/%m/%Y")} - {data_fine.strftime("%d/%m/%Y")}'
        else:
            mess += 1
            messages.warning(request, 'C\'è qualcosa che non va nei dati inseriti!')
    personeScambi = get_scambiPersona(request, data_inizio, data_fine)
    catScambi = get_scambiCat(request, data_inizio, data_fine)
    categorie_query = list(catScambi.keys())
    categorie = []
    for categoria in categorie_query:
        categorie.append(categoria.nome)
    numero_percat = list(catScambi.values())
    data_cat = {
        'cat_scambi': categorie,
        'numero_scambi': numero_percat
    }

    nomi_query= list(personeScambi.keys())
    nomi_scambi = []
    for nome in nomi_query:
        if not nome.tesoriere:
            nomi_scambi.append(nome.nome+" "+nome.cognome)
    numero_scambi = list(personeScambi.values())
    
    data = {
        'nomi_scambi': nomi_scambi,
        'numero_scambi': numero_scambi
    }
    context = {'bdt':bdt, 'form':form, 'scambi':scambi_periodo, 'periodo':periodo, 'personeScambi':json.dumps(data), 'catScambi':json.dumps(data_cat), 'mess':mess}
    return render(request, 'base/statistiche.html', context)

@login_required(login_url='/login')
def genera_xlsx_soci(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Soci'

    ws.append(['Cognome', 'Nome', 'Residenza', 'Telefono', 'Email', 'Quota', 'Ore date', 'Ore ricevute', 'Data primo scambio negli ultimi 12 mesi'])

    users = User.objects.filter(bdt=bdt).order_by('cognome')
    scambi = Scambio.objects.filter(bdt=bdt, data__range=[timezone.now().date()-timedelta(days=365), timezone.now().date()])
    date_scambi = []
    for user in users:
        if not user.tesoriere:
            date_scambi = []
            dati_user = saldo(user, scambi)
            ore_date = dati_user["ore_date"]
            ore_ricevute = dati_user["ore_ricevute"]
            for scambio in scambi:
                for donatore in scambio.donatori.all():
                    if user == donatore:
                        date_scambi.append(scambio.data)
                for ricevente in scambio.riceventi.all():
                    if user == ricevente:
                        date_scambi.append(scambio.data)
            date_scambi.sort()
            try:
                prima_data = date_scambi[0]
                prima_data = prima_data.strftime("%d/%m/%Y")
            except:
                prima_data = " "
            quota = ""
            if user.quota:
                quota = "Pagata"
            else:
                quota = "Non Pagata"
            ws.append([user.cognome, user.nome, user.residenza, user.telefono, user.email, quota, ore_date, ore_ricevute, prima_data])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=soci.xlsx'

    return response


@login_required(login_url='/login')
def genera_xlsx_scambi(request):
    bdt = BDT.objects.get(nome_bdt=request.user.bdt)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Soci'

    ws.append(['Data', 'Donatori', 'Riceventi', 'Durata', 'Categoria 1° liv.'])

    scambi = Scambio.objects.filter(bdt=bdt, data__range=[request.session['data_inizio'], request.session['data_fine']]).order_by('-data')
    for scambio in scambi:
        donatori = ""
        for donatore in scambio.donatori.all():
            if donatore.tesoriere:
                donatori += "Sig. Banca del Tempo "
            else:
                donatori += donatore.nome + " " + donatore.cognome + ", "
        riceventi = ""
        for ricevente in scambio.riceventi.all():
            if ricevente.tesoriere:
                riceventi += "Sig. Banca del Tempo "
            else:
                riceventi += ricevente.nome + " " + ricevente.cognome + ", "
        ws.append([scambio.data.strftime("%d/%m/%Y"), donatori, riceventi, scambio.durata, scambio.area.nome])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=scambi.xlsx'

    return response
