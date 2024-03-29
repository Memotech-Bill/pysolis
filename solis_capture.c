/* solis_capture.c - A program to capture data going from the Solis data logger to the cloud.
                     Revised to also capture data going the other way. */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>
#include <sys/stat.h>
#include <arpa/inet.h>
#include <pcap.h>

#define CAPSIZ  512

// Ethernet addresses are 6 bytes
#define MAC_LEN	6

// Ethernet header
typedef struct s_ethernet
    {
	u_char  dmac[MAC_LEN];          // Destination host address
	u_char  smac[MAC_LEN];          // Source host address
	u_short type;                   // IP? ARP? RARP? etc
    } H_ETHER;

// IP header
typedef struct s_ip
    {
	u_char          vhl;		    // version << 4 | header length >> 2
	u_char          tos;		    // type of service
	u_short         len;		    // total length
	u_short         id;		        // identification
	u_short         off;		    // fragment offset field
	u_char          ttl;		    // time to live
	u_char          pro;		    // protocol
	u_short         chk;		    // checksum
	struct in_addr  src;            // source and dest address
	struct in_addr  dst;            // source and dest address
    } H_IP;

#define IP_RF 0x8000		        // reserved fragment flag
#define IP_DF 0x4000		        // don't fragment flag
#define IP_MF 0x2000		        // more fragments flag
#define IP_OFFMASK 0x1fff	        // mask for fragmenting bits
#define IP_HL(ip)		(((ip)->vhl) & 0x0f)
#define IP_V(ip)		(((ip)->vhl) >> 4)

// TCP header

typedef u_int tcp_seq;

typedef struct s_tcp
    {
	u_short sport;	                // source port
	u_short dport;	                // destination port
	tcp_seq seq;		            // sequence number
	tcp_seq ack;		            // acknowledgement number
	u_char  off;	                // data offset, rsvd
	u_char  flags;
	u_short win;		            // window
	u_short chk;		            // checksum
	u_short urp;		            // urgent pointer
    } H_TCP;

#define TCP_OFF(tcp)    (((tcp)->off & 0xf0) >> 4)
#define TCP_FIN         0x01
#define TCP_SYN         0x02
#define TCP_RST         0x04
#define TCP_PUSH        0x08
#define TCP_ACK         0x10
#define TCP_URG         0x20
#define TCP_ECE         0x40
#define TCP_CWR         0x80
#define TCP_FLAGS       (TCP_FIN|TCP_SYN|TCP_RST|TCP_ACK|TCP_URG|TCP_ECE|TCP_CWR)

typedef struct s_msg
    {
    struct s_msg *  next;
    bool            cloud;
    u_int           nlen;
    tcp_seq         seq;
    bool            first;
    time_t          trecv;
    u_int           nseq;
    u_char          prev[1];
    } MSG;

MSG *msgfst = NULL;
MSG *msglst = NULL;

const char *psDir = ".";
FILE *pfLog = NULL;

const char *MacStr (char *sMac, const u_char *b)
    {
    sprintf (sMac, "%02X", b[0]);
    for (int i = 1; i < 6; ++i) sprintf (&sMac[3*i-1], ":%02X", b[i]);
    return sMac;
    }

const char *IPStr (char *sIP, const struct in_addr *addr)
    {
    const u_char *b = (const u_char *) &addr->s_addr;
    sprintf (sIP, "%d.%d.%d.%d", b[0], b[1], b[2], b[3]);
    return sIP;
    }

void LogMsg (const char *psFmt, ...)
    {
    va_list va;
    time_t t;
    if ( pfLog == NULL ) return;
    va_start (va, psFmt);
    time (&t);
    struct tm *now = gmtime (&t);
    fprintf (pfLog, "%04d/%02d/%02d %02d:%02d:%02d ", now->tm_year + 1900, now->tm_mon + 1,
        now->tm_mday, now->tm_hour, now->tm_min, now->tm_sec);
    vfprintf (pfLog, psFmt, va);
    fprintf (pfLog, "\n");
    fflush (pfLog);
    }

FILE *save_rec (FILE *f, const MSG *msg)
    {
    char sFile[256];
    time_t t;
    time (&t);
    // printf ("time = %d\n", t);
    struct tm *now = gmtime (&t);
    sprintf (sFile, "%s/%04d", psDir, now->tm_year + 1900);
    mkdir (sFile, 0750);
    sprintf (sFile, "%s/%04d/%02d", psDir, now->tm_year + 1900, now->tm_mon + 1);
    mkdir (sFile, 0750);
    sprintf (sFile, "%s/%04d/%02d/Solis_%04d%02d%02d.seq", psDir, now->tm_year + 1900, now->tm_mon + 1,
        now->tm_year + 1900, now->tm_mon + 1, now->tm_mday);
    FILE *fSeq = fopen (sFile, "ab");
    u_short head[2];
    head[0] = msg->cloud ? 'T' : 'R';
    head[1] = msg->nlen;
    fwrite (head, sizeof (u_short), 2, fSeq);
    fwrite (&msg->nseq, sizeof (msg->nseq), 1, fSeq);
    uint64_t t64 = msg->trecv;
    fwrite (&t64, sizeof (t64), 1, fSeq);
    fclose (fSeq);
    if ( fSeq == NULL )
        {
        LogMsg ("Unable to open file: %s", sFile);
        exit (1);
        }
    if ( f == NULL )
        {
        sprintf (sFile, "%s/%04d/%02d/Solis_%c%d_%04d%02d%02d.cap", psDir, now->tm_year + 1900, now->tm_mon + 1,
            msg->cloud ? 'T' : 'R', msg->nlen, now->tm_year + 1900, now->tm_mon + 1, now->tm_mday);
        // printf ("Open file: %s\n", sFile);
        f = fopen (sFile, "ab");
        if ( f == NULL )
            {
            LogMsg ("Unable to open file: %s", sFile);
            exit (1);
            }
        }
    // printf ("Write record.\n");
    head[0] = 0x5AA6;
    head[1] = msg->nlen;
    fwrite (head, sizeof (u_short), 2, f);
    fwrite (&t64, sizeof (t64), 1, f);
    fwrite (&msg->nseq, sizeof (msg->nseq), 1, f);
    fwrite (msg->prev, sizeof (u_char), msg->nlen, f);
    head[0] = 0xA559;
    fwrite (head, sizeof (u_short), 1, f);
    // printf ("Reccord complete.\n");
    return f;
    }

void capture (u_char *cfg, const struct pcap_pkthdr *ph, const u_char *pkt)
    {
    static u_int npkt = 0;
    // printf ("------------------------------------------------\n"
    //    "Packet number = %d, length = %d, captured = %d, time = %d.%06d\n",
    //    npkt, ph->len, ph->caplen, ph->ts.tv_sec, ph->ts.tv_usec);
    
    char sDst[18];
    char sSrc[18];
    const H_ETHER *eth = (const H_ETHER *) pkt;
    u_short type = ntohs (eth->type);
    // printf ("Ethernet: Destination = %s, Source = %s, Type = %04X\n",
    //     MacStr (sDst, eth->dmac), MacStr (sSrc, eth->smac), type);
    if ( type != 0x0800 ) return;

    pkt += sizeof (H_ETHER);
    const H_IP *ip = (const H_IP *) pkt;
    char sIPSrc[16];
    char sIPDst[16];
    u_int ip_hlen = 4 * IP_HL (ip);
    if ( ip_hlen < 20 )
        {
        // printf ("Invalid IP header length: %d\n", ip_hlen);
        return;
        }
    u_int plen = ntohs (ip->len);
    // printf ("IPv4: Version = %d, Header length = %d, DSCP = %02X, ECN = %02X, Length = %d\n",
    //     IP_V (ip), ip_hlen, ip->tos >> 2, ip->tos & 0x03, plen);
    u_short ip_ofs = ntohs (ip->off);
    // printf ("Identification = %04X, Flags = %02X, Offset = %d\n",
    // printf ("TTL = %d, Protocol = %02X, Checksum = %04X\n",
    //     ip->ttl, ip->pro, ntohs (ip->chk));
    // printf ("Source = %s, Destination = %s\n", IPStr (sIPSrc, &ip->src), IPStr (sIPDst, &ip->dst));
    if ( ip->pro != 0x06 ) return;
    bool cloud = memcmp (&ip->dst.s_addr, cfg, 4) == 0;

    pkt += ip_hlen;
    plen -= ip_hlen;
    const H_TCP *tcp = (const H_TCP *) pkt;
    u_int hlen = TCP_OFF (tcp);
    u_int ip_seq = ntohl (tcp->seq);
    // printf ("TCP: Source port = %d, Destination port = %d\n", ntohs (tcp->sport),
    //     ntohs (tcp->dport));
    // printf ("Sequence Num = %d, Ack Num = %d\n", ip_seq, ntohl (tcp->ack));
    // printf ("Data offset = %d, Flags = %02X, Window size = %d\n", hlen, tcp->flags, ntohs(tcp->win));
    // printf ("Checksum = %04X, Urgency pointer = %04X\n", ntohs (tcp->chk), ntohs (tcp->urp));

    pkt += 4 * hlen;
    plen -= 4 * hlen;
    // printf ("Payload size = %d\n", plen);
    if ( plen <= 0 ) return;

    MSG *msg = msgfst;
    // printf ("Payload size = %d\n", plen);
    while ( msg != NULL )
        {
        // printf ("msg = %p\n", msg);
        // printf ("msg->nlen = %d\n", msg->nlen);
        if (( msg->cloud == cloud ) && ( msg->nlen == plen )) break;
        msg = msg->next;
        }
    if ( msg == NULL )
        {
        // printf ("Allocate new message buffer\n");
        msg = (MSG *) malloc (sizeof (MSG) + plen);
        if ( msg == NULL )
            {
            LogMsg ("Unable to allocate message buffer for length %d", plen);
            exit (1);
            }
        msg->next = NULL;
        msg->cloud = cloud;
        msg->nlen = plen;
        msg->seq = ip_seq;
        msg->first = true;
        msg->trecv = ph->ts.tv_sec;
        msg->nseq = ++npkt;
        memcpy (msg->prev, pkt, plen);
        // printf ("Message buffer created: msg = %p\n", msg);
        if ( msgfst == NULL )
            {
            msgfst = msg;
            msglst = msg;
            }
        else
            {
            msglst->next = msg;
            msglst = msg;
            }
        // printf ("msgfst = %p, msglst = %p\n", msgfst, msglst);
        return;
        }
    if ( ip_seq == msg->seq ) return;
    FILE *f = NULL;
    if ( msg->first )
        {
        // printf ("Save first record.\n");
        f = save_rec (f, msg);
        msg->first = false;
        }
    msg->seq = ip_seq;
    if ( memcmp (pkt, msg->prev, msg->nlen) )
        {
        // printf ("Save new record.\n");
        msg->trecv = ph->ts.tv_sec;
        msg->nseq = ++npkt;
        memcpy (msg->prev, pkt, plen);
        f = save_rec (f, msg);
        }
    if ( f != NULL ) fclose (f);
    }

int main (int nArg, const char *psArg[])
    {
    u_char cfg[4];                      // Inverter IP address
    char errbuf[PCAP_ERRBUF_SIZE];      // Error message
	bpf_u_int32 mask;		            // Interface netmask
	bpf_u_int32 net;		            // Interface IP
	struct bpf_program fp;		        // Compiled PCap filter

    // Destination directory

    if ( nArg > 3 ) psDir = psArg[3];

    // IP Address of inverter

    sscanf (psArg[2], "%hhd.%hhd.%hhd.%hhd", &cfg[0], &cfg[1], &cfg[2], &cfg[3]);

    // Log file

    if ( nArg > 4 )
        {
        pfLog = fopen (psArg[4], "a");
        }
    if (pfLog == NULL) pfLog = stderr;
    LogMsg ("solis_capture started");
    LogMsg ("Capture device: %s", psArg[1]);
    LogMsg ("Inverter address: %d.%d.%d.%d", cfg[0], cfg[1], cfg[2], cfg[3]);
    LogMsg ("Destination directory: %s", psDir);

	// Find the properties for the device
    
	if ( pcap_lookupnet (psArg[1], &net, &mask, errbuf) == -1 )
        {
		LogMsg ("Couldn't get netmask for device %s: %s", psArg[1], errbuf);
        return 1;
        }
    
	// Open the session in non-promiscuous mode
    
    pcap_t *pc = pcap_open_live (psArg[1], BUFSIZ, 0, 1000, errbuf);
    if ( pc == NULL )
        {
        LogMsg ("Failed to open %s for live capture: %s", psArg[1], errbuf);
        return 1;
        }

    // Get the header type

    int dlt = pcap_datalink (pc);
    // LogMsg ("Header type: %d", dlt);
    if ( dlt != DLT_EN10MB )
        {
        fprintf(pfLog, "Device %s doesn't provide Ethernet headers\n", psArg[1]);
        return 1;
        }

    // Compile and apply the filter

    char sFilter[60];
    // sprintf (sFilter, "src host %s and dst port 10000 and len >= 61", psArg[2]);
    // sprintf (sFilter, "host %s and port 10000 and len >= 61", psArg[2]);
    sprintf (sFilter, "host %s and port 443 and len >= 61", psArg[2]);
	if ( pcap_compile (pc, &fp, sFilter, 0, net) == -1 )
        {
		LogMsg ("Couldn't parse filter %s: %s", sFilter, pcap_geterr (pc));
		return 1;
        }
    
	if ( pcap_setfilter (pc, &fp) == -1 )
        {
		LogMsg ("Couldn't install filter %s: %s", psArg[2], pcap_geterr (pc));
		return 1;
        }

    // Capture packets

    LogMsg ("Start of capture");
    // if ( pcap_loop (pc, -1, capture, (u_char *) NULL) < 0 )
    if ( pcap_loop (pc, -1, capture, cfg) < 0 )
        {
        LogMsg ("Failed to start packet capture: %s", pcap_geterr (pc));
        return 1;
        }

    // Clean up

    LogMsg ("End of capture");
    pcap_close (pc);

    return 0;
    }
