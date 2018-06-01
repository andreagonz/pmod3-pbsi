import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from django.conf import settings
import datetime

def genera_mensaje(sitio, fromadd, toadd):
    """
    Se genera el mensaje destinado para la cuenta de abuso
    """
    msgRoot = MIMEMultipart('related')
    msgRoot['Subject'] = 'Alerta de phishig'
    msgRoot['From'] = fromadd
    msgRoot['To'] = toadd
    msgRoot.preamble = 'This is a multi-part message in MIME format.'
    msgAlternative = MIMEMultipart('alternative')
    msgRoot.attach(msgAlternative)
    msgText = MIMEText('Captura de pantalla.')
    msgAlternative.attach(msgText)
    st = 'Fecha: %s<br/>Se encontró actividad sospechosa de ser phishing relacionada ' \
         + 'a la URL %s con la dirección IP %s. Por favor revisar indicios de actividad' \
         + ' maliciosa en el servidor correspondiente.' \
         + '<br/>'
    st += 'Se adjunta una captura de pantalla de la página en cuestión:<br/><br/>' \
          + '<img src="cid:image1">'
    captura = os.path.join(settings.BASE_DIR, sitio.captura[1:])
    fp = open(captura, 'rb')
    msgImage = MIMEImage(fp.read())
    fp.close()
    msgImage.add_header('Content-ID', '<image1>')
    msgRoot.attach(msgImage)
    msgText = MIMEText(st % (datetime.datetime.now(), '. '.join(sitio.url.split('.')), sitio.ip), 'html')
    msgAlternative.attach(msgText)
    return msgRoot.as_string()

def manda_correo(correo, msg):
    """
    Se envia un correo con el mensaje especificado
    """
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    usr = 'irc.perl.bot@gmail.com'
    passw = '**pbsi_irc**'
    server.login(usr, passw)
    server.sendmail(usr, correo, msg)
    server.quit()
