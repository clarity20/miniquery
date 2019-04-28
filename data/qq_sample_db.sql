-- MySQL dump 10.16  Distrib 10.1.30-MariaDB, for CYGWIN (x86_64)
--
-- Host: 127.0.0.1    Database: qq_sample_db
-- ------------------------------------------------------
-- Server version       5.6.35-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `table1`
--

DROP TABLE IF EXISTS `table1`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `table1` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(20) DEFAULT NULL,
  `zipcode` char(6) DEFAULT NULL,
  `rating` decimal(8,4) DEFAULT NULL,
  `rateCode` char(2) DEFAULT NULL,
  `activationDate` date DEFAULT NULL,
  `activationTime` time DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `table1`
--

LOCK TABLES `table1` WRITE;
/*!40000 ALTER TABLE `table1` DISABLE KEYS */;
INSERT INTO `table1` VALUES (1,'Beverly Hills','90210',3.8001,'A3',NULL,NULL),(2,'South Orange','07079',0.2990,'B4','2019-02-14','12:00:00'),(3,'Lexington','40502',4.3333,'A7','2017-12-12',NULL),(4,'New York','10033',-2.7735,'A3','2014-11-03','19:55:13'),(5,'Faketown','98765',7.0000,NULL,'2016-05-21',NULL),(6,'Lexington','40503',1.6701,'D2','2014-05-30','08:15:00'),(7,'Houston','77005',10.1139,'E1','2019-01-15',NULL),(8,'Abilene','79601',4.5009,NULL,NULL,NULL),(9,'Honolulu','96805',3.0990,'B6','2013-09-18',NULL);
/*!40000 ALTER TABLE `table1` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2019-03-11 11:15:12
